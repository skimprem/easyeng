from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model

from dictionary.languages import LANGUAGES

from .models import Text


class TextForm(forms.ModelForm):
    class Meta:
        model = Text
        fields = ["title", "author", "language", "content"]
        widgets = {"content": forms.Textarea(attrs={"class": "md-input", "spellcheck": "false"})}


class UploadForm(forms.Form):
    file = forms.FileField(label="Файл", help_text=".txt или .md, в кодировке UTF-8")
    title = forms.CharField(label="Название", required=False, max_length=300, help_text="по умолчанию — имя файла")
    language = forms.ChoiceField(label="Язык", choices=LANGUAGES, initial="en")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if Path(f.name).suffix.lower() not in (".txt", ".md", ".markdown"):
            raise forms.ValidationError("Поддерживаются файлы .txt и .md")
        if f.size > settings.MAX_TEXT_UPLOAD_BYTES:
            raise forms.ValidationError("Файл слишком большой")
        raw = f.read()
        for enc in ("utf-8-sig", "cp1251", "latin-1"):
            try:
                self.cleaned_data["decoded"] = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        return f


class ShareForm(forms.Form):
    recipient = forms.CharField(label="Имя пользователя получателя", max_length=150)
    message = forms.CharField(label="Сообщение", max_length=500, required=False, widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, sender=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.sender = sender

    def clean_recipient(self):
        username = self.cleaned_data["recipient"].strip()
        user = get_user_model().objects.filter(username__iexact=username, is_active=True).first()
        if user is None:
            raise forms.ValidationError("Такого пользователя нет")
        if user == self.sender:
            raise forms.ValidationError("Нельзя отправить текст самому себе")
        return user
