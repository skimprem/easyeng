from django.contrib import admin

from .models import Card


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("word", "translation", "user", "box", "due", "reviews", "lapses")
    list_filter = ("box", "src_lang", "tgt_lang")
    search_fields = ("word", "translation")
