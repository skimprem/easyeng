import random

from django.utils import timezone

from .models import MAX_BOX, Card

RANDOM_CHECK_SHARE = 0.2  # доля внеплановых проверок выученного в сессии
RANDOM_CHECK_MAX = 5


def due_cards(user, now=None):
    return Card.objects.filter(user=user, due__lte=now or timezone.now())


def build_session(user, limit=20, practice=False):
    """Набор карточек для сессии повторения.

    Обычная сессия: карточки, которым пора (сначала «учу», затем по сроку),
    плюс несколько случайных уже знакомых слов — проверка, что они не угаданы.
    practice=True: случайные карточки без учёта расписания (когда всё повторено).
    Возвращает список (card, early).
    """
    now = timezone.now()
    if practice:
        ids = list(Card.objects.filter(user=user).values_list("id", flat=True))
        picked = random.sample(ids, min(limit, len(ids)))
        cards = Card.objects.filter(id__in=picked)
        return [(c, c.due > now) for c in sorted(cards, key=lambda c: picked.index(c.id))]

    due = list(due_cards(user, now).order_by("box", "due")[:limit])
    n_checks = min(RANDOM_CHECK_MAX, max(1, round(len(due) * RANDOM_CHECK_SHARE))) if due else 0
    checks = []
    if n_checks:
        candidates = list(Card.objects.filter(user=user, box__gte=2, due__gt=now).values_list("id", flat=True))
        picked = random.sample(candidates, min(n_checks, len(candidates)))
        checks = list(Card.objects.filter(id__in=picked))
    session = [(c, False) for c in due]
    # Проверки вставляем в случайные места, чтобы их нельзя было предсказать
    for c in checks:
        session.insert(random.randint(0, len(session)), (c, True))
    return session


def stats(user):
    now = timezone.now()
    cards = Card.objects.filter(user=user)
    return {
        "total": cards.count(),
        "learning": cards.filter(box=0).count(),
        "reviewing": cards.filter(box__gt=0).exclude(box=MAX_BOX).count(),
        "mastered": cards.filter(box=MAX_BOX).count(),
        "due": cards.filter(due__lte=now).count(),
        "next_due": cards.filter(due__gt=now).order_by("due").values_list("due", flat=True).first(),
    }
