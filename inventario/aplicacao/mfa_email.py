"""Código de seis dígitos via SMTP, limitado por usuário e vinculado à sessão."""

from datetime import timedelta
import hashlib
import hmac
import logging
import re
import secrets
import smtplib
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita
from inventario.models import DispositivoEmail

LOGGER = logging.getLogger(__name__)
VALIDADE = 300
INTERVALO = 60
JANELA = 900
MAX_ENVIOS = 5
MAX_TENTATIVAS = 5
BLOQUEIO = 900


class ErroMFAEmail(ValueError):
    pass


def hash_email(email):
    return hashlib.sha256((email or "").strip().casefold().encode("utf-8")).hexdigest()


def email_valido(email):
    try:
        validate_email((email or "").strip())
        return True
    except (ValidationError, TypeError):
        return False


def configuracao_valida():
    if not settings.SAURON_EMAIL_ENABLED:
        raise ErroMFAEmail(
            "É necessário configurar o envio de e-mail no servidor; consulte o guia de instalação."
        )
    if (
        not settings.EMAIL_HOST
        or not 1 <= settings.EMAIL_PORT <= 65535
        or not email_valido(settings.DEFAULT_FROM_EMAIL)
        or settings.EMAIL_USE_TLS == settings.EMAIL_USE_SSL
    ):
        raise ErroMFAEmail(
            "Configuração SMTP incompleta: confira host, porta, remetente e TLS/SSL."
        )


def codigo_assinado(usuario_id, nonce, email, codigo):
    texto = f"{usuario_id}|{nonce}|{hash_email(email)}|{codigo}".encode()
    chave = hmac.new(settings.SECRET_KEY.encode(), b"sauron:mfa-email:v1", hashlib.sha256).digest()
    return hmac.new(chave, texto, hashlib.sha256).hexdigest()


def mascarar(email):
    if not email_valido(email):
        return "não cadastrado"
    local, dominio = email.strip().rsplit("@", 1)
    return local[:1] + "***@" + dominio


def desafio_pendente(usuario):
    dispositivo = DispositivoEmail.objects.filter(user=usuario).first()
    if (
        dispositivo
        and dispositivo.codigo_hash
        and dispositivo.expira_em
        and dispositivo.expira_em > timezone.now()
        and dispositivo.email_hash == hash_email(usuario.email)
    ):
        return dispositivo.nonce
    return ""


def adotar_desafio_inicial(usuario):
    """O código criado antes do primeiro login só pode ser vinculado uma vez."""
    with transaction.atomic():
        travar_escrita()
        dispositivo = DispositivoEmail.objects.select_for_update().filter(user=usuario).first()
        if (
            not dispositivo
            or not dispositivo.pode_adotar
            or not dispositivo.codigo_hash
            or not dispositivo.expira_em
            or dispositivo.expira_em <= timezone.now()
            or dispositivo.email_hash != hash_email(usuario.email)
        ):
            return ""
        dispositivo.pode_adotar = False
        dispositivo.save(update_fields=["pode_adotar"])
        return dispositivo.nonce


def enviar_codigo(usuario, inicial=False):
    configuracao_valida()
    with transaction.atomic():
        travar_escrita()
        atual = get_user_model().objects.select_for_update().get(pk=usuario.pk)
        if not atual.is_active or not email_valido(atual.email):
            raise ErroMFAEmail("Cadastre um endereço de e-mail válido para esta conta.")
        dispositivo, _ = DispositivoEmail.objects.select_for_update().get_or_create(
            user=atual, defaults={"name": "E-mail", "confirmed": False}
        )
        agora = timezone.now()
        if dispositivo.bloqueado_ate and agora < dispositivo.bloqueado_ate:
            raise ErroMFAEmail("Muitas tentativas. Aguarde 15 minutos antes de tentar novamente.")
        if dispositivo.reenviar_apos and agora < dispositivo.reenviar_apos:
            raise ErroMFAEmail("Aguarde um minuto antes de solicitar outro código.")
        if not dispositivo.janela_inicio or agora - dispositivo.janela_inicio >= timedelta(
            seconds=JANELA
        ):
            dispositivo.janela_inicio = agora
            dispositivo.envios_janela = 0
        if dispositivo.envios_janela >= MAX_ENVIOS:
            raise ErroMFAEmail("Limite de envios atingido. Aguarde o fim da janela de 15 minutos.")
        if dispositivo.bloqueado_ate and agora >= dispositivo.bloqueado_ate:
            dispositivo.bloqueado_ate = None
            dispositivo.tentativas = 0
        if dispositivo.email_confirmado_hash != hash_email(atual.email):
            dispositivo.confirmed = False
        codigo = f"{secrets.randbelow(1_000_000):06d}"
        nonce = secrets.token_hex(32)
        dispositivo.nonce = nonce
        dispositivo.pode_adotar = inicial
        dispositivo.email_hash = hash_email(atual.email)
        dispositivo.codigo_hash = codigo_assinado(atual.pk, nonce, atual.email, codigo)
        dispositivo.expira_em = agora + timedelta(seconds=VALIDADE)
        dispositivo.reenviar_apos = agora + timedelta(seconds=INTERVALO)
        dispositivo.envios_janela += 1
        dispositivo.save()
        destinatario = atual.email.strip()
    try:
        enviados = send_mail(
            "Sauron — código de verificação",
            f"Seu código de verificação é: {codigo}\n\nEle expira em 5 minutos e pode ser usado uma vez. Se você não iniciou o acesso, ignore esta mensagem.",
            settings.DEFAULT_FROM_EMAIL,
            [destinatario],
            fail_silently=False,
        )
        if enviados != 1:
            raise OSError("O servidor não aceitou a mensagem.")
    except (OSError, smtplib.SMTPException, ValueError) as erro:
        with transaction.atomic():
            travar_escrita()
            dispositivo = DispositivoEmail.objects.select_for_update().get(user_id=usuario.pk)
            if dispositivo.nonce == nonce:
                dispositivo.codigo_hash = ""
                dispositivo.nonce = ""
                dispositivo.pode_adotar = False
                dispositivo.expira_em = None
                dispositivo.reenviar_apos = None
                dispositivo.save(update_fields=["codigo_hash", "nonce", "pode_adotar", "expira_em", "reenviar_apos"])
        LOGGER.warning("Envio MFA por e-mail falhou: %s", type(erro).__name__)
        registrar_evento("MFA_EMAIL_ENVIO_FALHOU", "Autenticacao", usuario.username)
        raise ErroMFAEmail(
            "Não foi possível enviar o código. Verifique a configuração SMTP e tente novamente."
        ) from erro
    registrar_evento("MFA_EMAIL_ENVIADO", "Autenticacao", usuario.username)
    return nonce


def verificar_codigo(usuario, nonce, codigo, senha):
    credencial = get_user_model().objects.filter(pk=usuario.pk).only("password").first()
    senha_valida = bool(credencial and credencial.check_password(senha))
    with transaction.atomic():
        travar_escrita()
        atual = get_user_model().objects.select_for_update().get(pk=usuario.pk)
        dispositivo = DispositivoEmail.objects.select_for_update().filter(user=atual).first()
        if dispositivo is None:
            return None
        agora = timezone.now()
        if dispositivo.bloqueado_ate and agora < dispositivo.bloqueado_ate:
            return None
        if dispositivo.bloqueado_ate and agora >= dispositivo.bloqueado_ate:
            dispositivo.bloqueado_ate = None
            dispositivo.tentativas = 0
        valido = (
            atual.is_active
            and isinstance(nonce, str)
            and bool(nonce)
            and hmac.compare_digest(dispositivo.nonce, nonce)
            and isinstance(codigo, str)
            and bool(re.fullmatch(r"[0-9]{6}", codigo))
            and bool(dispositivo.codigo_hash)
            and dispositivo.expira_em is not None
            and agora < dispositivo.expira_em
            and dispositivo.email_hash == hash_email(atual.email)
            and senha_valida
            and hmac.compare_digest(atual.password, credencial.password)
            and hmac.compare_digest(
                dispositivo.codigo_hash, codigo_assinado(atual.pk, nonce, atual.email, codigo)
            )
        )
        if valido:
            dispositivo.confirmed = True
            dispositivo.email_confirmado_hash = hash_email(atual.email)
            dispositivo.codigo_hash = ""
            dispositivo.nonce = ""
            dispositivo.pode_adotar = False
            dispositivo.expira_em = None
            dispositivo.tentativas = 0
            dispositivo.bloqueado_ate = None
            dispositivo.reenviar_apos = None
            dispositivo.save()
            registrar_evento("MFA_EMAIL_VERIFICADO", "Autenticacao", atual.username)
            return dispositivo
        dispositivo.tentativas += 1
        if dispositivo.tentativas >= MAX_TENTATIVAS:
            dispositivo.bloqueado_ate = agora + timedelta(seconds=BLOQUEIO)
            dispositivo.codigo_hash = ""
            dispositivo.nonce = ""
            dispositivo.pode_adotar = False
            dispositivo.expira_em = None
        dispositivo.save()
        registrar_evento("MFA_EMAIL_FALHOU", "Autenticacao", atual.username)
        return None
