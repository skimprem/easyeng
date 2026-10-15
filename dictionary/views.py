import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from . import freedict
from .forms import DictionaryUploadForm
from .importers import ImportError_, import_dictionary
from .languages import LANGUAGE_CODES
from .models import Dictionary
from .service import lookup
from .text import clean_word, normalize_key


@login_required
@require_GET
def lookup_view(request):
    word = clean_word(request.GET.get("w", ""))
    profile = request.user.profile
    src = request.GET.get("src") or profile.source_lang
    tgt = request.GET.get("tgt") or profile.target_lang
    if not word:
        return JsonResponse({"error": "Выделите слово"}, status=400)
    if src not in LANGUAGE_CODES or tgt not in LANGUAGE_CODES:
        return JsonResponse({"error": "Неизвестный язык"}, status=400)
    result = lookup(word, src, tgt, user=request.user)
    result["vocab"] = _vocab_card(request.user, src, tgt, result)
    return JsonResponse(result)


def _vocab_card(user, src, tgt, result):
    """Есть ли слово (в любой из найденных форм) в личном словарике."""
    from vocab.models import Card  # словарик — надстройка над словарями, импорт локальный

    keys = {normalize_key(w) for w in result["forms"]} | {normalize_key(r["headword"]) for r in result["results"]}
    card = Card.objects.filter(user=user, src_lang=src, tgt_lang=tgt, key__in=keys).first()
    return {"id": card.id, "word": card.word, "translation": card.translation} if card else None


@login_required
def dictionary_list(request):
    dictionaries = Dictionary.objects.filter(Q(owner__isnull=True) | Q(owner=request.user))
    form = DictionaryUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["file"]
        with tempfile.TemporaryDirectory(prefix="easyeng-upload-") as tmp:
            path = Path(tmp) / Path(upload.name).name
            with path.open("wb") as f:
                for chunk in upload.chunks():
                    f.write(chunk)
            try:
                d = import_dictionary(
                    path,
                    form.cleaned_data["source_lang"],
                    form.cleaned_data["target_lang"],
                    owner=request.user,
                    name=form.cleaned_data["name"] or None,
                )
            except ImportError_ as e:
                messages.error(request, str(e))
            else:
                messages.success(request, f"Словарь «{d.name}» загружен: {d.entry_count} статей")
                return redirect("dictionary:list")
    return render(request, "dictionary/list.html", {"dictionaries": dictionaries, "form": form})


def _own_or_staff(request, pk):
    d = get_object_or_404(Dictionary, pk=pk)
    if d.owner_id != request.user.id and not (d.is_shared and request.user.is_staff):
        raise Http404
    return d


@login_required
@require_POST
def dictionary_toggle(request, pk):
    d = _own_or_staff(request, pk)
    d.enabled = not d.enabled
    d.save(update_fields=["enabled"])
    return redirect("dictionary:list")


@login_required
@require_POST
def dictionary_delete(request, pk):
    d = _own_or_staff(request, pk)
    d.delete()
    messages.success(request, f"Словарь «{d.name}» удалён")
    return redirect("dictionary:list")


@staff_member_required
def freedict_catalog(request):
    if request.method == "POST":
        name = request.POST.get("name", "")
        try:
            d = freedict.install(name)
        except Exception as e:
            messages.error(request, f"Не удалось установить {name}: {e}")
        else:
            messages.success(request, f"Установлен «{d.name}»: {d.entry_count} статей")
        return redirect("dictionary:freedict")
    try:
        items = freedict.catalog()
    except Exception as e:
        items = []
        messages.error(request, f"Каталог FreeDict недоступен: {e}")
    installed = set(Dictionary.objects.filter(owner__isnull=True).values_list("name", flat=True))
    for item in items:
        item["installed"] = f"FreeDict {item['name']} {item['version']}" in installed
    return render(request, "dictionary/freedict.html", {"items": items})
