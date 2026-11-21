from django.core.management.base import BaseCommand, CommandError

from inventario.aplicacao.risco import gravar_snapshot_risco


class Command(BaseCommand):
    help = "Registra um novo snapshot do risco puro atual."

    def handle(self, *args, **options):
        try:
            snapshot = gravar_snapshot_risco()
        except ValueError as erro:
            raise CommandError(str(erro)) from erro
        self.stdout.write(f"Snapshot {snapshot.pk}: risco total = {snapshot.risco_total:.6f}")
