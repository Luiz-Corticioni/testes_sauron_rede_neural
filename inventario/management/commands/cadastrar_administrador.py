"""Cadastro inicial explícito, local e sem exigir autenticador previamente instalado."""
from getpass import getpass
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from inventario.aplicacao.administrador_inicial import cadastrar_primeiro_administrador


class Command(BaseCommand):
    help = 'Cadastra somente o primeiro administrador local, sem login/MFA; não inicia sessão.'

    def add_arguments(self, parser):
        parser.add_argument('--usuario')
        parser.add_argument('--email', default='')

    def handle(self, *args, **options):
        if get_user_model().objects.filter(is_superuser=True).exists():
            raise CommandError('Já existe administrador; use a administração autenticada para criar outros.')
        nome = options['usuario'] or input('Nome do primeiro administrador: ')
        senha = getpass('Senha: ')
        if senha != getpass('Confirme a senha: '):
            raise CommandError('As senhas não coincidem.')
        try:
            usuario = cadastrar_primeiro_administrador(nome, senha, options['email'])
        except ValidationError as erro:
            raise CommandError('; '.join(erro.messages)) from erro
        self.stdout.write(f'Administrador {usuario.username} cadastrado sem exigir MFA para a criação. Nenhuma sessão foi iniciada.')
        self.stdout.write('Nesta versão de apresentação, entre com usuário e senha; o MFA está desativado.')
