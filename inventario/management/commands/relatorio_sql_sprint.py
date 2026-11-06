import json

from django.core.management.base import BaseCommand

from inventario.infraestrutura.consultas_sprint import incidencias_por_ativo


class Command(BaseCommand):
    help = "Relatório SQL didático parametrizado, somente leitura."

    def add_arguments(self, parser):
        parser.add_argument("--limiar", type=float, default=0)

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(incidencias_por_ativo(options["limiar"]), ensure_ascii=False, indent=2))
