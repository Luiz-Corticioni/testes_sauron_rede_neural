"""Carga local em processo isolado: não cria auditoria nova para permissões restauradas."""
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db.models.signals import m2m_changed

from inventario.infraestrutura.auditoria import conectar_sinais_autenticacao


class Command(BaseCommand):
    help = "Carrega uma fixture de restauração em banco temporário criado pelo restaurador."

    def add_arguments(self, parser):
        parser.add_argument('arquivo')

    def handle(self, *args, **options):
        banco = settings.DATABASES['default']
        caminho = Path(banco['NAME']).resolve()
        if (banco['ENGINE'] != 'django.db.backends.sqlite3' or caminho.name != 'restaurado.sqlite3'
                or not caminho.parent.name.startswith('restauracao-')
                or Path(settings.DATA_DIR).resolve() != caminho.parent / 'dados'):
            raise CommandError('A carga de restauração exige banco temporário isolado.')
        usuario = get_user_model()
        relacoes = (usuario.groups.through, usuario.user_permissions.through, Group.permissions.through)
        try:
            for relacao in relacoes:
                m2m_changed.disconnect(sender=relacao, dispatch_uid=f'audit.m2m.{relacao.__name__}')
            call_command('loaddata', options['arquivo'], stdout=self.stdout)
        finally:
            conectar_sinais_autenticacao()
