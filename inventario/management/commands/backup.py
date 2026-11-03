import sqlite3

from django.core.management.base import BaseCommand, CommandError

from inventario.infraestrutura.backup import backup_sqlite


class Command(BaseCommand):
    help = "Cria backup lógico cifrado em dados/backups; chave Fernet obrigatória."

    def add_arguments(self, parser):
        parser.add_argument("--retencao", type=int)

    def handle(self, *args, **options):
        try:
            caminho = backup_sqlite(options["retencao"])
        except (OSError, ValueError, TimeoutError, sqlite3.Error) as erro:
            raise CommandError(str(erro)) from erro
        self.stdout.write(self.style.SUCCESS(f"Backup criado: {caminho}"))
