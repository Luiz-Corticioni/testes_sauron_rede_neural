from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction
from inventario.infraestrutura.exportacao import colecoes_json, inventario_completo
from inventario.infraestrutura.arquivos import salvar_json_atomico
from inventario.infraestrutura.auditoria import registrar_evento


class Command(BaseCommand):
    help = "Exporta inventário explicitamente, com destino obrigatório e auditoria."

    def add_arguments(self, parser):
        parser.add_argument("--saida", required=True)
        parser.add_argument("--legado", action="store_true", help="Somente as quatro coleções históricas.")

    def handle(self, *args, **options):
        with transaction.atomic():
            dados = colecoes_json() if options["legado"] else inventario_completo()
        salvar_json_atomico(Path(options["saida"]), dados)
        registrar_evento("EXPORTAR_INVENTARIO", "Inventario", "json", {"saida": options["saida"]})
        self.stdout.write(options["saida"])
