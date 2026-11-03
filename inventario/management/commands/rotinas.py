import json

from django.core.management.base import BaseCommand

from inventario.infraestrutura.auditoria import usar_usuario
from inventario.aplicacao.rotinas import executar_rotinas


class Command(BaseCommand):
    help = "Executa rotinas operacionais; --sem-rede usa apenas caches locais."

    def add_arguments(self, parser):
        parser.add_argument("--sem-rede", action="store_true")

    def handle(self, *args, **options):
        # Comando de administração local: ações automáticas têm autor nulo na trilha.
        with usar_usuario(None):
            resultado = executar_rotinas(sem_rede=options["sem_rede"])
        self.stdout.write(json.dumps(resultado, ensure_ascii=False, indent=2))
