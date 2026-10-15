from django.contrib import admin

from .models import Dictionary


@admin.register(Dictionary)
class DictionaryAdmin(admin.ModelAdmin):
    list_display = ("name", "source_lang", "target_lang", "owner", "entry_count", "enabled")
    list_filter = ("source_lang", "target_lang", "enabled")
