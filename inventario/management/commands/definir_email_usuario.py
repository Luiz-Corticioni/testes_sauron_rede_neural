"""Recuperação local: configura o endereço de uma conta existente com auditoria."""

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction


class Command(BaseCommand):
    help = "Cadastra ou altera o e-mail de uma conta existente; execute localmente no servidor."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True)
        parser.add_argument("--email", required=True)

    def handle(self, *args, **options):
        email = options["email"].strip()
        try:
            validate_email(email)
        except ValidationError as erro:
            raise CommandError("Informe um endereço de e-mail válido.") from erro
        with transaction.atomic():
            usuario = (
                get_user_model()
                .objects.select_for_update()
                .filter(username=options["usuario"])
                .first()
            )
            if not usuario:
                raise CommandError("Usuário não encontrado.")
            usuario.email = email
            usuario.save(update_fields=["email"])
        self.stdout.write(
            "Endereço atualizado. Se o SMTP estiver configurado, o código será enviado; confira a caixa de entrada e a página de MFA."
        )
