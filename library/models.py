from django.conf import settings
from django.db import models

from dictionary.languages import LANGUAGES

from .markdown import render_markdown


class Text(models.Model):
    SOURCE_CHOICES = [
        ("manual", "Создан вручную"),
        ("upload", "Загружен из файла"),
        ("gutenberg", "Project Gutenberg"),
        ("shared", "Получен от пользователя"),
    ]

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="texts")
    title = models.CharField("Название", max_length=300)
    author = models.CharField("Автор", max_length=300, blank=True)
    language = models.CharField("Язык", max_length=8, choices=LANGUAGES, default="en")
    content = models.TextField("Текст (Markdown)", blank=True)
    content_html = models.TextField(editable=False, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    source_url = models.URLField(blank=True, max_length=500)
    progress = models.FloatField(default=0)  # позиция чтения, 0..1
    # Закреплённые над словами переводы: [{"o": смещение в тексте, "w": слово, "t": перевод}]
    glosses = models.JSONField(default=list, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    last_read = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_read", "-updated"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.content_html = render_markdown(self.content)
        if "update_fields" in kwargs and kwargs["update_fields"] is not None and "content" in kwargs["update_fields"]:
            kwargs["update_fields"] = {*kwargs["update_fields"], "content_html"}
        super().save(*args, **kwargs)

    @property
    def word_count(self):
        return len(self.content.split())

    def copy_for(self, user):
        return Text.objects.create(
            owner=user,
            title=self.title,
            author=self.author,
            language=self.language,
            content=self.content,
            source="shared",
            source_url=self.source_url,
        )


class Share(models.Model):
    PENDING, ACCEPTED, DECLINED = "pending", "accepted", "declined"
    STATUS_CHOICES = [(PENDING, "Ожидает"), (ACCEPTED, "Принят"), (DECLINED, "Отклонён")]

    text = models.ForeignKey(Text, on_delete=models.CASCADE, related_name="shares")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_shares")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_shares")
    message = models.CharField("Сообщение", max_length=500, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
