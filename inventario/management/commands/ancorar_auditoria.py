from django.core.management.base import BaseCommand
from inventario.infraestrutura.ancoras import ancorar


class Command(BaseCommand):
    help = "Ancora a cabeça atual em arquivo append-only e syslog configurável."

    def handle(self, *args, **options):
        self.stdout.write(str(ancorar()))

