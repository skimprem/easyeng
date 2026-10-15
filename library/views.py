import json
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from dictionary.languages import LANGUAGES

from .forms import ShareForm, TextForm, UploadForm
from .markdown import plain_text_to_markdown, render_markdown
from .models import Share, Text
from .sources import gutenberg


def _own_text(request, pk):
    return get_object_or_404(Text, pk=pk, owner=request.user)


@login_required
def text_list(request):
    texts = Text.objects.filter(owner=request.user).defer("content", "content_html")
    q = request.GET.get("q", "").strip()
    if q:
        texts = texts.filter(Q(title__icontains=q) | Q(author__icontains=q))
    return render(request, "library/list.html", {"texts": texts, "q": q})


@login_required
def text_read(request, pk):
    text = _own_text(request, pk)
    Text.objects.filter(pk=text.pk).update(last_read=timezone.now())
    profile = request.user.profile
    return render(
        request,
        "library/read.html",
        {
            "text": text,
            "languages": LANGUAGES,
            "src": text.language,
            "tgt": profile.target_lang if profile.target_lang != text.language else profile.source_lang,
        },
    )


@login_required
@require_POST
def text_progress(request, pk):
    text = _own_text(request, pk)
    try:
        value = float(json.loads(request.body).get("progress", 0))
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({"error": "bad progress"}, status=400)
    Text.objects.filter(pk=text.pk).update(progress=min(max(value, 0.0), 1.0))
    return JsonResponse({"ok": True})


MAX_GLOSSES = 5000


def _parse_glosses(raw):
    """Проверяет список закреплённых переводов из читалки. None — если формат неверный."""
    if not isinstance(raw, list) or len(raw) > MAX_GLOSSES:
        return None
    result = []
    for g in raw:
        if not isinstance(g, dict):
            return None
        o, w, t = g.get("o"), g.get("w"), g.get("t")
        if not (isinstance(o, int) and o >= 0 and isinstance(w, str) and isinstance(t, str)):
            return None
        w, t = w.strip()[:200], t.strip()[:200]
        if w and t:
            result.append({"o": o, "w": w, "t": t})
    return sorted(result, key=lambda g: g["o"])


@login_required
@require_POST
def text_glosses(request, pk):
    """Автосохранение закреплённых переводов: заменяет весь список (пустой — сброс)."""
    text = _own_text(request, pk)
    try:
        glosses = _parse_glosses(json.loads(request.body).get("glosses"))
    except (ValueError, AttributeError):
        glosses = None
    if glosses is None:
        return JsonResponse({"error": "bad glosses"}, status=400)
    Text.objects.filter(pk=text.pk).update(glosses=glosses)
    return JsonResponse({"ok": True, "count": len(glosses)})


@login_required
def text_create(request):
    initial = {"language": request.user.profile.source_lang}
    form = TextForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        text = form.save(commit=False)
        text.owner = request.user
        text.source = "manual"
        text.save()
        return redirect("library:read", pk=text.pk)
    return render(request, "library/edit.html", {"form": form, "is_new": True})


@login_required
def text_edit(request, pk):
    text = _own_text(request, pk)
    form = TextForm(request.POST or None, instance=text)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Сохранено")
        return redirect("library:read", pk=text.pk)
    return render(request, "library/edit.html", {"form": form, "text": text})


@login_required
@require_POST
def markdown_preview(request):
    return HttpResponse(render_markdown(request.POST.get("content", "")))


@login_required
@require_POST
def text_delete(request, pk):
    text = _own_text(request, pk)
    text.delete()
    messages.success(request, f"«{text.title}» удалён")
    return redirect("library:list")


@login_required
def text_upload(request):
    form = UploadForm(request.POST or None, request.FILES or None, initial={"language": request.user.profile.source_lang})
    if request.method == "POST" and form.is_valid():
        f = form.cleaned_data["file"]
        raw = form.cleaned_data["decoded"]
        is_md = Path(f.name).suffix.lower() in (".md", ".markdown")
        text = Text.objects.create(
            owner=request.user,
            title=form.cleaned_data["title"] or Path(f.name).stem,
            language=form.cleaned_data["language"],
            content=raw if is_md else plain_text_to_markdown(raw),
            source="upload",
        )
        return redirect("library:read", pk=text.pk)
    return render(request, "library/upload.html", {"form": form})


@login_required
def gutenberg_search(request):
    q = request.GET.get("q", "").strip()
    lang = request.GET.get("lang", "en")
    page = request.GET.get("page", "1")
    page = max(int(page), 1) if page.isdigit() else 1
    result, error = None, None
    if q:
        try:
            result = gutenberg.search(q, language=lang or None, page=page)
        except Exception as e:
            error = f"Project Gutenberg недоступен: {e}"
    return render(
        request,
        "library/gutenberg.html",
        {"q": q, "lang": lang, "page": page, "result": result, "error": error, "languages": LANGUAGES},
    )


@login_required
@require_POST
def gutenberg_import(request):
    book_id = gutenberg.parse_book_id(request.POST.get("book_id", ""))
    if book_id is None:
        messages.error(request, "Укажите номер книги или ссылку вида https://www.gutenberg.org/ebooks/1661")
        return redirect("library:gutenberg")
    try:
        data = gutenberg.fetch(book_id)
    except Exception as e:
        messages.error(request, f"Не удалось загрузить книгу: {e}")
        return redirect("library:gutenberg")
    text = Text.objects.create(owner=request.user, source="gutenberg", **data)
    messages.success(request, f"«{text.title}» добавлена в библиотеку")
    return redirect("library:read", pk=text.pk)


@login_required
def text_share(request, pk):
    text = _own_text(request, pk)
    form = ShareForm(request.POST or None, sender=request.user)
    if request.method == "POST" and form.is_valid():
        recipient = form.cleaned_data["recipient"]
        Share.objects.create(text=text, sender=request.user, recipient=recipient, message=form.cleaned_data["message"])
        messages.success(request, f"«{text.title}» отправлен пользователю {recipient.username}")
        return redirect("library:list")
    return render(request, "library/share.html", {"form": form, "text": text})


@login_required
def inbox(request):
    incoming = Share.objects.filter(recipient=request.user).select_related("text", "sender")[:100]
    outgoing = Share.objects.filter(sender=request.user).select_related("text", "recipient")[:100]
    return render(request, "library/inbox.html", {"incoming": incoming, "outgoing": outgoing})


@login_required
@require_POST
def share_respond(request, pk):
    share = get_object_or_404(Share, pk=pk, recipient=request.user, status=Share.PENDING)
    if request.POST.get("action") == "accept":
        copy = share.text.copy_for(request.user)
        share.status = Share.ACCEPTED
        share.save(update_fields=["status"])
        messages.success(request, f"«{copy.title}» добавлен в вашу библиотеку")
        return redirect("library:read", pk=copy.pk)
    share.status = Share.DECLINED
    share.save(update_fields=["status"])
    return redirect("library:inbox")
