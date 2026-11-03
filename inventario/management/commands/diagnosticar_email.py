"""Verifica configuração SMTP; só envia mensagem mediante opção explícita."""
import smtplib
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from inventario.aplicacao.mfa_email import configuracao_valida, ErroMFAEmail


class Command(BaseCommand):
    help="Verifica a configuração de e-mail; --enviar-para envia um teste ao endereço indicado."

    def add_arguments(self,parser):
        parser.add_argument("--enviar-para",help="Endereço que deve receber a mensagem de teste.")

    def handle(self,*args,**options):
        try:
            configuracao_valida()
        except ErroMFAEmail as erro:
            raise CommandError(str(erro)) from erro
        self.stdout.write("Configuração SMTP preenchida; senha não exibida. Para testar a entrega, use --enviar-para SEU_EMAIL.")
        destino=options["enviar_para"]
        if not destino:
            return
        try:
            validate_email(destino)
            enviados=send_mail("Sauron — teste de e-mail", "Esta é uma mensagem de teste da configuração de e-mail do Sauron. Não contém código de acesso.",
                               settings.DEFAULT_FROM_EMAIL,[destino],fail_silently=False)
            if enviados!=1:
                raise OSError("Mensagem não aceita.")
        except (ValidationError,OSError,smtplib.SMTPException,ValueError) as erro:
            raise CommandError("Não foi possível enviar a mensagem; confira endereço e configuração SMTP.") from erro
        self.stdout.write("O servidor aceitou o envio. Confira a caixa de entrada e a pasta de spam do destinatário.")
