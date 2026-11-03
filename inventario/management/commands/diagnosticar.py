"""Diagnóstico operacional: um código de saída não zero impede uma publicação inválida."""

import json
from django.core.management.base import BaseCommand, CommandError
from inventario.infraestrutura.diagnostico import verificar_instalacao


class Command(BaseCommand):
    help = 'Verifica dados, banco, migrações, templates e arquivos estáticos.'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **options):
        resultado = verificar_instalacao()
        if options['json']:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False))
        else:
            for item in resultado['verificacoes']:
                self.stdout.write(f"{'OK' if item['ok'] else 'FALHA'} · {item['nome']}: {item['detalhe']}")
        if not resultado['ok']:
            raise CommandError('Instalação incompleta. Execute preparar_servidor; confira permissões e os logs se a falha persistir.')
        if not options['json']:
            self.stdout.write(self.style.SUCCESS('Instalação verificada.'))
