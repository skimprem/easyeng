from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from dictionary.languages import LANGUAGES
from dictionary.providers.registry import DEFAULT_PROVIDER_ORDER


def default_providers():
    return list(DEFAULT_PROVIDER_ORDER)


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    source_lang = models.CharField("Язык текстов", max_length=8, choices=LANGUAGES, default="en")
    target_lang = models.CharField("Язык перевода", max_length=8, choices=LANGUAGES, default="ru")
    # Порядок опроса словарей: ключи провайдеров из реестра
    providers = models.JSONField("Словари", default=default_providers)
    auto_add_pinned = models.BooleanField(
        "Добавлять закреплённые слова в словарик", default=True,
        help_text="Закрепили перевод над словом — значит, слово незнакомое: оно сразу попадёт на карточки.",
    )
    session_size = models.PositiveSmallIntegerField(
        "Карточек за одно повторение", default=20,
        validators=[MinValueValidator(5), MaxValueValidator(200)],
    )

    def __str__(self):
        return f"Профиль {self.user}"
