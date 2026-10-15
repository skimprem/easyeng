from django.core.management.base import BaseCommand

from dictionary import freedict


class Command(BaseCommand):
    help = "Скачать и установить общий словарь из FreeDict. Без аргументов — показать каталог."

    def add_arguments(self, parser):
        parser.add_argument("names", nargs="*", help="напр. eng-rus rus-eng")

    def handle(self, names, **opts):
        if not names:
            for e in freedict.catalog():
                self.stdout.write(f"{e['name']:10} {e['headwords']:>8} слов  v{e['version']}")
            return
        for name in names:
            self.stdout.write(f"Скачиваю {name}...")
            d = freedict.install(name)
            self.stdout.write(self.style.SUCCESS(f"Установлен «{d.name}»: {d.entry_count} статей"))
