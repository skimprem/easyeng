from django.contrib import admin

from .models import Share, Text


@admin.register(Text)
class TextAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "owner", "language", "source", "updated")
    list_filter = ("language", "source")
    search_fields = ("title", "author")


@admin.register(Share)
class ShareAdmin(admin.ModelAdmin):
    list_display = ("text", "sender", "recipient", "status", "created")
