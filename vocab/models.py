from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from dictionary.languages import LANGUAGES

# Интервалы повторения по коробкам Лейтнера (в днях).
# Коробка 0 — «учу»: слово показывается, пока не ответишь правильно.
# Даже выученные слова (последняя коробка) изредка возвращаются — защита от угадывания.
INTERVALS = [0, 1, 3, 7, 21, 60]
MAX_BOX = len(INTERVALS) - 1


class Card(models.Model):
    LEARNING, REVIEWING, MASTERED = "learning", "reviewing", "mastered"
    STATUS_NAMES = {LEARNING: "Учу", REVIEWING: "Повторяю", MASTERED: "Выучено"}

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cards")
    word = models.CharField("Слово", max_length=200)  # словарная форма — лицевая сторона
    key = models.CharField(max_length=200, editable=False)
    translation = models.CharField("Перевод", max_length=500)
    form = models.CharField("Как встретилось", max_length=200, blank=True)  # went для go
    context = models.TextField("Контекст", blank=True)  # предложение из текста
    src_lang = models.CharField(max_length=8, choices=LANGUAGES, default="en")
    tgt_lang = models.CharField(max_length=8, choices=LANGUAGES, default="ru")
    text = models.ForeignKey("library.Text", null=True, blank=True, on_delete=models.SET_NULL, related_name="cards")

    box = models.PositiveSmallIntegerField(default=0)
    due = models.DateTimeField(default=timezone.now)
    reviews = models.PositiveIntegerField(default=0)
    lapses = models.PositiveIntegerField(default=0)  # сколько раз «забыл» уже знакомое слово
    last_reviewed = models.DateTimeField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
        constraints = [
            models.UniqueConstraint(fields=["user", "src_lang", "tgt_lang", "key"], name="unique_card_per_user")
        ]
        indexes = [models.Index(fields=["user", "due"])]

    def __str__(self):
        return f"{self.word} — {self.translation}"

    def save(self, *args, **kwargs):
        from dictionary.text import normalize_key

        self.key = normalize_key(self.word)
        super().save(*args, **kwargs)

    @property
    def status(self):
        if self.box == 0:
            return self.LEARNING
        return self.MASTERED if self.box == MAX_BOX else self.REVIEWING

    @property
    def status_name(self):
        return self.STATUS_NAMES[self.status]

    def answer(self, correct, early=False, now=None):
        """Ответ на карточку.

        correct=True  («вправо»): в следующую коробку, повтор через INTERVALS[box] дней.
        correct=False («влево»): обратно в коробку 0 — на заучивание, повтор сразу.
        early=True — внеплановая проверка выученного слова: верный ответ расписание
        не сдвигает, неверный — возвращает слово на заучивание.
        """
        now = now or timezone.now()
        self.reviews += 1
        self.last_reviewed = now
        if correct:
            if not early:
                self.box = min(self.box + 1, MAX_BOX)
                self.due = now + timedelta(days=INTERVALS[self.box])
        else:
            if self.box > 0:
                self.lapses += 1
            self.box = 0
            self.due = now
        self.save()

    def to_review_dict(self):
        return {
            "id": self.id,
            "word": self.word,
            "form": self.form,
            "translation": self.translation,
            "context": self.context,
            "box": self.box,
            "src": self.src_lang,
            "tgt": self.tgt_lang,
        }
