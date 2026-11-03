from django.core.management.base import BaseCommand

from inventario.cli import SauronCLI


class Command(BaseCommand):
    help = "Executa a interface completa de terminal do Sauron."

    def handle(self, *args, **options):
        SauronCLI().executar()
