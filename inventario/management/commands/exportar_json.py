from django.core.management.base import BaseCommand
from inventario.infraestrutura.exportacao import exportar_inventario_json
from inventario.infraestrutura.auditoria import registrar_evento


class Command(BaseCommand):
    help = "Exportação explícita dos arrays legados para um diretório."

    def add_arguments(self, parser):
        parser.add_argument("--saida", required=True)

    def handle(self, *args, **options):
        resultado = exportar_inventario_json(options["saida"])
        registrar_evento("EXPORTAR_JSON", "Inventario", "legado", {"saida": options["saida"]})
        self.stdout.write(str(resultado))
