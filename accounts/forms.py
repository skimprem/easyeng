from django import forms
from django.contrib.auth.forms import UserCreationForm

from dictionary.providers.registry import available_providers

from .models import Profile


class SignupForm(UserCreationForm):
    email = forms.EmailField(label="Email", required=False)

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")


class ProfileForm(forms.ModelForm):
    providers = forms.MultipleChoiceField(
        label="Словари",
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Опрашиваются сверху вниз — перетащите, чтобы изменить порядок.",
    )

    class Meta:
        model = Profile
        fields = ["source_lang", "target_lang", "providers", "auto_add_pinned", "session_size"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        providers = available_providers()
        # Порядок: сначала включённые в сохранённом порядке, затем остальные
        order = list(self.instance.providers or []) if self.instance and self.instance.pk else []
        providers.sort(key=lambda p: order.index(p.key) if p.key in order else len(order))
        self.fields["providers"].choices = [(p.key, p.name) for p in providers]
        self.provider_info = {p.key: p for p in providers}

    def provider_items(self):
        """Для шаблона: [(key, name, description, online, checked)] в текущем порядке."""
        selected = set(self["providers"].value() or [])
        return [
            (key, name, self.provider_info[key].description, self.provider_info[key].online, key in selected)
            for key, name in self.fields["providers"].choices
        ]

    def clean(self):
        data = super().clean()
        if data.get("source_lang") and data.get("source_lang") == data.get("target_lang"):
            self.add_error("target_lang", "Языки должны различаться")
        return data
