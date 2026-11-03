from django.core.management.base import BaseCommand, CommandError
from inventario.infraestrutura.auditoria import verificar_cadeia


class Command(BaseCommand):
    help = "Verifica hashes e aponta o primeiro elo quebrado da auditoria."

    def add_arguments(self, parser):
        parser.add_argument("--somente-cadeia", action="store_true",
                            help="Verifica restauração isolada sem atestar âncoras externas.")

    def handle(self, *args, **options):
        resultado = verificar_cadeia(verificar_ancora=not options["somente_cadeia"])
        if not resultado["integra"]:
            raise CommandError(f"Cadeia/âncora inválida: elo {resultado['primeiro_elo_quebrado']}, {resultado.get('ancora', '')}.")
        self.stdout.write(f"Cadeia íntegra: {resultado['verificados']} registros verificados. Âncora: {resultado.get('ancora', 'não verificada')}.")
