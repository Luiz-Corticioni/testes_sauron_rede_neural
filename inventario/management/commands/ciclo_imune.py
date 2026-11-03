import json
from django.core.management.base import BaseCommand
from inventario.aplicacao.imune import executar_ciclo


class Command(BaseCommand):
    help = "Executa o recomendador imune local, sem consultar a rede."

    def handle(self, *args, **options):
        self.stdout.write(json.dumps(executar_ciclo(), ensure_ascii=False))
