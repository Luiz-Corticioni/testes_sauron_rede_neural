"""Dispositivo de e-mail: só armazena HMAC do código temporário, nunca o código."""

from django.conf import settings
from django.db import models
from django_otp.models import Device


class DispositivoEmail(Device):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dispositivo_email"
    )
    confirmed = models.BooleanField(default=False)
    codigo_hash = models.CharField(max_length=64, blank=True)
    nonce = models.CharField(max_length=64, blank=True)
    pode_adotar = models.BooleanField(default=False)
    email_hash = models.CharField(max_length=64, blank=True)
    email_confirmado_hash = models.CharField(max_length=64, blank=True)
    expira_em = models.DateTimeField(null=True, blank=True)
    reenviar_apos = models.DateTimeField(null=True, blank=True)
    janela_inicio = models.DateTimeField(null=True, blank=True)
    envios_janela = models.PositiveSmallIntegerField(default=0)
    tentativas = models.PositiveSmallIntegerField(default=0)
    bloqueado_ate = models.DateTimeField(null=True, blank=True)

    def verify_token(self, token):
        # A verificação exige também senha e nonce da sessão e é feita pelo serviço.
        return False
