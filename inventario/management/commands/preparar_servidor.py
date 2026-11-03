"""Prepara uma instalação nova ou atualizada antes de servir páginas."""

from pathlib import Path
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Cria diretórios, aplica migrações, configura grupos e publica CSS/JS.'

    def add_arguments(self, parser):
        parser.add_argument('--sem-estaticos', action='store_true', help='Imagem Docker com collectstatic já executado no build.')
        parser.add_argument('--sem-aquecer-cache', action='store_true', help='Adia o pré-carregamento das análises comuns.')

    def handle(self, *args, **options):
        try:
            settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
            banco = settings.DATABASES["default"]
            if banco["ENGINE"] == "django.db.backends.sqlite3" and str(banco["NAME"]) != ":memory:":
                Path(banco["NAME"]).parent.mkdir(parents=True, exist_ok=True)
            call_command('check', stdout=self.stdout)
            call_command('migrate', interactive=False, stdout=self.stdout)
            call_command('configurar_grupos', stdout=self.stdout)
            if not options['sem_estaticos']:
                call_command('collectstatic', interactive=False, stdout=self.stdout)
            call_command('diagnosticar', stdout=self.stdout)
            if not options.get('sem_aquecer_cache', False):
                call_command('aquecer_cache', stdout=self.stdout)
        except OSError as erro:
            raise CommandError('Sem permissão para preparar os diretórios da instalação.') from erro
