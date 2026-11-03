"""Provisiona o e-mail de novas contas e agenda envio somente após commit."""

import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save, pre_save
from inventario.aplicacao.mfa_email import email_valido, enviar_codigo, ErroMFAEmail
from inventario.models import DispositivoEmail

LOGGER = logging.getLogger(__name__)


def email_anterior(sender, instance, raw=False, using="default", update_fields=None, **kwargs):
    if hasattr(instance, "_email_anterior"):
        delattr(instance, "_email_anterior")
    if raw or not instance.pk or (update_fields is not None and "email" not in update_fields):
        return
    instance._email_anterior = (
        sender.objects.using(using).filter(pk=instance.pk).values_list("email", flat=True).first()
    )


def novo_usuario(sender, instance, created, raw=False, using="default", **kwargs):
    if raw:
        return
    anterior = getattr(instance, "_email_anterior", None)
    alterado = (
        not created
        and anterior is not None
        and anterior.strip().casefold() != (instance.email or "").strip().casefold()
    )
    if not created and not alterado:
        return
    if not email_valido(instance.email):
        if alterado:
            DispositivoEmail.objects.using(using).filter(user_id=instance.pk).update(
                confirmed=False,
                codigo_hash="",
                nonce="",
                pode_adotar=False,
                expira_em=None,
                email_confirmado_hash="",
            )
        return
    dispositivo, _ = DispositivoEmail.objects.using(using).get_or_create(
        user_id=instance.pk, defaults={"name": "E-mail", "confirmed": False}
    )
    if alterado:
        dispositivo.confirmed = False
        dispositivo.codigo_hash = ""
        dispositivo.nonce = ""
        dispositivo.pode_adotar = False
        dispositivo.expira_em = None
        dispositivo.email_confirmado_hash = ""
        dispositivo.save(
            update_fields=[
                "confirmed",
                "codigo_hash",
                "nonce",
                "pode_adotar",
                "expira_em",
                "email_confirmado_hash",
            ]
        )
    if not settings.SAURON_EMAIL_ENABLED:
        return
    usuario_id = instance.pk

    def enviar_apos_commit():
        usuario = (
            get_user_model().objects.using(using).filter(pk=usuario_id, is_active=True).first()
        )
        from inventario.seguranca_mfa import usuario_privilegiado
        if usuario and not usuario_privilegiado(usuario):
            try:
                enviar_codigo(usuario, inicial=True)
            except ErroMFAEmail:
                LOGGER.warning(
                    "Código inicial por e-mail não enviado; o usuário pode solicitar novamente."
                )

    transaction.on_commit(enviar_apos_commit, using=using)


def conectar():
    pre_save.connect(
        email_anterior,
        sender=get_user_model(),
        weak=False,
        dispatch_uid="sauron.mfa.email.anterior",
    )
    post_save.connect(
        novo_usuario,
        sender=get_user_model(),
        weak=False,
        dispatch_uid="sauron.mfa.email.novo_usuario",
    )
