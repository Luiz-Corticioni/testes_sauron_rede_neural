import json
from django.core.management.base import BaseCommand, CommandError
from inventario.infraestrutura.implantacao import verificar_implantacao


class Command(BaseCommand):
    help = 'Verifica pré-requisitos locais de produção sem expor segredos ou enviar mensagens.'

    def add_arguments(self, parser):
        parser.add_argument('--json', action='store_true')

    def handle(self, *args, **options):
        resultado = verificar_implantacao()
        if options['json']:
            self.stdout.write(json.dumps(resultado, ensure_ascii=False))
        else:
            for item in resultado['verificacoes']:
                self.stdout.write(f"{'OK' if item['ok'] else 'FALHA'}: {item['nome']}: {item['detalhe']}")
            self.stdout.write('Homologação manual necessária: ' + '; '.join(resultado['validacao_manual']))
        if not resultado['ok']:
            raise CommandError('Pré-requisitos de produção incompletos; consulte as verificações.')
