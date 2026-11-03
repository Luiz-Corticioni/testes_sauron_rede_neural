"""Sincronização opcional, independente de rotinas e da simulação."""
import json
from django.core.management.base import BaseCommand, CommandError
from inventario.aplicacao.epss import sincronizar_epss


class Command(BaseCommand):
    help = "Atualiza EPSS explicitamente; indisponibilidade preserva dados e gera aviso."
    def handle(self, *args, **options):
        resultado = sincronizar_epss()
        self.stdout.write(json.dumps(resultado, ensure_ascii=False))
        if resultado["avisos"]:
            raise CommandError("Sincronização EPSS incompleta; dados anteriores preservados. Consulte os avisos.")
