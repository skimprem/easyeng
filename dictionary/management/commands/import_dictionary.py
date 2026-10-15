from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from dictionary.importers import ImportError_, import_dictionary


class Command(BaseCommand):
    help = "Импортировать локальный словарь (StarDict/TSV, можно архивом). Без --user — общий словарь."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--src", required=True, help="код языка оригинала, напр. en")
        parser.add_argument("--tgt", required=True, help="код языка перевода, напр. ru")
        parser.add_argument("--name")
        parser.add_argument("--user", help="имя пользователя-владельца")

    def handle(self, path, src, tgt, name=None, user=None, **opts):
        owner = None
        if user:
            owner = get_user_model().objects.filter(username=user).first()
            if owner is None:
                raise CommandError(f"Нет пользователя {user}")
        try:
            d = import_dictionary(path, src, tgt, owner=owner, name=name)
        except ImportError_ as e:
            raise CommandError(str(e)) from e
        self.stdout.write(self.style.SUCCESS(f"Импортирован «{d.name}»: {d.entry_count} статей"))
