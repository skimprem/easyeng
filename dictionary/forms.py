from django import forms
from django.conf import settings

from .languages import LANGUAGES


class DictionaryUploadForm(forms.Form):
    file = forms.FileField(
        label="Файл словаря",
        help_text="StarDict (архив .zip/.tar.* с .ifo/.idx/.dict) или TSV: слово<TAB>перевод1; перевод2",
    )
    name = forms.CharField(label="Название", required=False, max_length=200)
    source_lang = forms.ChoiceField(label="С языка", choices=LANGUAGES, initial="en")
    target_lang = forms.ChoiceField(label="На язык", choices=LANGUAGES, initial="ru")

    def clean_file(self):
        f = self.cleaned_data["file"]
        if f.size > settings.MAX_DICTIONARY_UPLOAD_BYTES:
            raise forms.ValidationError("Файл слишком большой")
        return f
