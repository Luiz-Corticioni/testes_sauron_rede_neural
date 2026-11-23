import json
from django.core.management.base import BaseCommand, CommandError
from inventario.aplicacao.backtest import gravar_novo, ler_executar


class Command(BaseCommand):
    help = "Compara prioridades com arquivos históricos locais, sem acessar banco ou rede."

    def add_arguments(self, parser):
        parser.add_argument("entrada")
        parser.add_argument("--orcamento", type=int, required=True)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument("--saida")

    def handle(self, *args, **opcoes):
        try:
            resultado = ler_executar(opcoes["entrada"], opcoes["orcamento"], opcoes["seed"])
            if opcoes["saida"]:
                gravar_novo(opcoes["saida"], resultado)
                self.stdout.write("Resultado escrito em arquivo novo.")
            else:
                self.stdout.write(json.dumps(resultado, ensure_ascii=True, indent=2, allow_nan=False))
        except (ValueError, OSError, RecursionError, TypeError) as erro:
            raise CommandError(str(erro)) from erro
