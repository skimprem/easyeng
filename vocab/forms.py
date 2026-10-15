from django import forms

from .models import Card


class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ["word", "translation", "context", "src_lang", "tgt_lang"]
        labels = {"src_lang": "Язык слова", "tgt_lang": "Язык перевода"}
        widgets = {"context": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean(self):
        from dictionary.text import normalize_key

        data = super().clean()
        if data.get("word") and self.user:
            dup = Card.objects.filter(
                user=self.user, src_lang=data.get("src_lang"), tgt_lang=data.get("tgt_lang"),
                key=normalize_key(data["word"]),
            ).exclude(pk=self.instance.pk)
            if dup.exists():
                self.add_error("word", "Это слово уже есть в словарике")
        return data
