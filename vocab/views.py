import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dictionary.languages import LANGUAGE_CODES
from dictionary.text import normalize_key
from library.models import Text

from .forms import CardForm
from .models import MAX_BOX, Card
from .services import build_session, stats

FILTERS = {
    "learning": Q(box=0),
    "reviewing": Q(box__gt=0) & ~Q(box=MAX_BOX),
    "mastered": Q(box=MAX_BOX),
}


@login_required
def card_list(request):
    cards = Card.objects.filter(user=request.user)
    status = request.GET.get("status", "")
    if status in FILTERS:
        cards = cards.filter(FILTERS[status])
    q = request.GET.get("q", "").strip()
    if q:
        cards = cards.filter(Q(word__icontains=q) | Q(translation__icontains=q) | Q(form__icontains=q))
    page = Paginator(cards, 50).get_page(request.GET.get("page"))
    profile = request.user.profile
    form = CardForm(user=request.user, initial={"src_lang": profile.source_lang, "tgt_lang": profile.target_lang})
    return render(request, "vocab/list.html", {
        "page": page, "status": status, "q": q, "stats": stats(request.user), "form": form, "max_box": MAX_BOX,
    })


@login_required
@require_POST
def card_create(request):
    form = CardForm(request.POST, user=request.user)
    if form.is_valid():
        card = form.save(commit=False)
        card.user = request.user
        card.save()
        messages.success(request, f"«{card.word}» добавлено в словарик")
    else:
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
    return redirect("vocab:list")


@login_required
@require_POST
def card_add_api(request):
    """Добавление слова из читалки. Если слово уже есть — возвращает существующую карточку."""
    try:
        data = json.loads(request.body)
        word = str(data.get("word", "")).strip()[:200]
        translation = str(data.get("translation", "")).strip()[:500]
        src, tgt = data.get("src"), data.get("tgt")
    except (ValueError, AttributeError):
        return JsonResponse({"error": "bad request"}, status=400)
    if not word or not translation or src not in LANGUAGE_CODES or tgt not in LANGUAGE_CODES:
        return JsonResponse({"error": "bad request"}, status=400)
    text = None
    if str(data.get("text_id", "")).isdigit():
        text = Text.objects.filter(pk=int(data["text_id"]), owner=request.user).first()
    card, created = Card.objects.get_or_create(
        user=request.user, src_lang=src, tgt_lang=tgt, key=normalize_key(word),
        defaults={
            "word": word,
            "translation": translation,
            "form": str(data.get("form", "")).strip()[:200],
            "context": str(data.get("context", "")).strip()[:1000],
            "text": text,
        },
    )
    if not created and translation.lower() not in card.translation.lower():
        # Новый вариант перевода дополняет карточку
        card.translation = f"{card.translation}; {translation}"[:500]
        card.save(update_fields=["translation"])
    return JsonResponse({"id": card.id, "created": created, "word": card.word, "translation": card.translation})


@login_required
def card_edit(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)
    form = CardForm(request.POST or None, instance=card, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Карточка сохранена")
        return redirect("vocab:list")
    return render(request, "vocab/edit.html", {"form": form, "card": card})


@login_required
@require_POST
def card_delete(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)
    card.delete()
    messages.success(request, f"«{card.word}» удалено из словарика")
    return redirect(request.POST.get("next") or "vocab:list")


@login_required
@require_POST
def card_relearn(request, pk):
    """Вернуть слово на заучивание вручную."""
    card = get_object_or_404(Card, pk=pk, user=request.user)
    card.answer(correct=False)
    return redirect(request.POST.get("next") or "vocab:list")


@login_required
def review(request):
    practice = request.GET.get("mode") == "practice"
    session = build_session(request.user, limit=request.user.profile.session_size, practice=practice)
    cards = [dict(card.to_review_dict(), early=early) for card, early in session]
    return render(request, "vocab/review.html", {
        "cards": cards, "practice": practice, "stats": stats(request.user),
        "direction": request.GET.get("dir", "forward"),
    })


@login_required
@require_POST
def card_answer(request, pk):
    card = get_object_or_404(Card, pk=pk, user=request.user)
    try:
        data = json.loads(request.body)
    except ValueError:
        return JsonResponse({"error": "bad request"}, status=400)
    card.answer(correct=bool(data.get("correct")), early=bool(data.get("early")))
    return JsonResponse({"id": card.id, "box": card.box, "due": card.due.isoformat(), "status": card.status})
