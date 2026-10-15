from django.conf import settings
from django.db import models

from .languages import LANGUAGES


class Dictionary(models.Model):
    """Локальный словарь, импортированный из файла (StarDict, TSV, ...).

    owner = None — общий словарь, доступен всем пользователям
    (ставит администратор, например из каталога FreeDict).
    """

    name = models.CharField("Название", max_length=200)
    source_lang = models.CharField("С языка", max_length=8, choices=LANGUAGES)
    target_lang = models.CharField("На язык", max_length=8, choices=LANGUAGES)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="dictionaries"
    )
    format = models.CharField(max_length=20)
    description = models.TextField(blank=True)
    entry_count = models.PositiveIntegerField(default=0)
    enabled = models.BooleanField("Включён", default=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["source_lang", "target_lang", "name"]
        verbose_name_plural = "dictionaries"

    def __str__(self):
        return f"{self.name} ({self.source_lang}→{self.target_lang})"

    @property
    def is_shared(self):
        return self.owner_id is None


class DictionaryEntry(models.Model):
    dictionary = models.ForeignKey(Dictionary, on_delete=models.CASCADE, related_name="entries")
    headword = models.CharField(max_length=255)
    key = models.CharField(max_length=255)  # нормализованный headword для поиска
    definition = models.TextField()  # безопасный (санитизированный) HTML

    class Meta:
        indexes = [models.Index(fields=["dictionary", "key"])]
