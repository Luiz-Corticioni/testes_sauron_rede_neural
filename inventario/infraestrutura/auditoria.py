"""Autoria por contexto e cadeia SHA-256 que detecta alteração de elos."""

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
import hmac
from django.conf import settings
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.db import connections
from django.db.models.signals import post_delete, post_save

AUTOR = ContextVar("sauron_autor", default=None)


def definir_usuario(usuario):
    identificador = usuario.pk if usuario and usuario.is_authenticated else None
    return AUTOR.set(identificador)


@contextmanager
def usar_usuario(usuario):
    token = definir_usuario(usuario)
    try:
        yield
    finally:
        AUTOR.reset(token)


def travar_escrita(using="default"):
    """Primeira operação é uma escrita: serializa o commit-check e a cadeia no SQLite."""
    with connections[using].cursor() as cursor:
        if connections[using].vendor == "postgresql":
            cursor.execute("SELECT pg_advisory_xact_lock(1396786514)")
            return
        if connections[using].vendor != "sqlite":
            raise ValueError("Backend de escrita não suportado.")
        cursor.execute("INSERT OR IGNORE INTO inventario_travadominio (id, versao) VALUES (1, 0)")
        cursor.execute("UPDATE inventario_travadominio SET versao = versao + 1 WHERE id = 1")


def calcular_hash(registro):
    conteudo = {
        "id": registro.pk,
        "usuario_id": registro.usuario_id,
        "acao": registro.acao,
        "entidade": registro.entidade,
        "entidade_id": registro.entidade_id,
        "detalhes": registro.detalhes,
        "ocorrido_em": registro.ocorrido_em.isoformat(),
    }
    canonico = json.dumps(
        conteudo,
        cls=DjangoJSONEncoder,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    mensagem = (canonico + registro.hash_anterior).encode("utf-8")
    versao = getattr(registro, "cadeia_versao", 1)
    if versao == 1:
        return hashlib.sha256(mensagem).hexdigest()
    if versao != 2:
        raise ValueError("Versão de cadeia desconhecida.")
    return hmac.new(settings.SAURON_AUDIT_HMAC_KEY.encode(), b"v2:"+mensagem, hashlib.sha256).hexdigest()


def preparar_registro(registro, using):
    from inventario.models import RegistroAuditoria

    travar_escrita(using)
    anterior = RegistroAuditoria.objects.using(using).order_by("id").last()
    registro.pk = anterior.pk + 1 if anterior else 1
    registro.cadeia_versao = 2
    registro.hash_anterior = anterior.hash if anterior else ""
    registro.hash = calcular_hash(registro)


def registrar_evento(acao, entidade, entidade_id, detalhes=None):
    from inventario.models import RegistroAuditoria

    return RegistroAuditoria.objects.create(
        usuario_id=AUTOR.get(),
        acao=acao,
        entidade=entidade,
        entidade_id=str(entidade_id)[:80],
        detalhes=detalhes or {},
    )


def verificar_cadeia(verificar_ancora=True):
    from inventario.models import RegistroAuditoria

    anterior = ""
    quantidade = 0
    for registro in RegistroAuditoria.objects.order_by("id").iterator():
        quantidade += 1
        try:
            valido = registro.hash_anterior == anterior and registro.hash == calcular_hash(registro)
        except (ValueError, TypeError, UnicodeError):
            valido = False
        if not valido:
            return {
                "integra": False,
                "primeiro_elo_quebrado": registro.pk,
                "verificados": quantidade,
            }
        anterior = registro.hash
    if verificar_ancora:
        from inventario.infraestrutura.ancoras import verificar_ancoras
        integra, ancora = verificar_ancoras()
        return {"integra": integra, "primeiro_elo_quebrado": None, "verificados": quantidade,
                "ancora": ancora}
    return {"integra": True, "primeiro_elo_quebrado": None, "verificados": quantidade}


def dados_objeto(objeto):
    dados = {
        campo.attname: getattr(objeto, campo.attname) for campo in objeto._meta.concrete_fields
    }
    for campo in ("password", "key", "token", "secret"):
        if campo in dados:
            dados[campo] = "<omitido>"
    return json.loads(json.dumps(dados, cls=DjangoJSONEncoder))


def auditar_salvamento(sender, instance, created, raw=False, **kwargs):
    if not raw:
        registrar_evento(
            "CRIAR" if created else "ALTERAR", sender.__name__, instance.pk, dados_objeto(instance)
        )


def auditar_exclusao(sender, instance, **kwargs):
    if sender.__name__ == "Anticorpo" and instance.origem_id:
        from inventario.models import Incidencia
        Incidencia.objects.filter(pk=instance.origem_id).update(imune_aprendida=False)
    registrar_evento("REMOVER", sender.__name__, instance.pk, dados_objeto(instance))


def conectar_sinais():
    conectar_sinais_autenticacao()
    from inventario.models import (
        Ativo,
        CertificadoDigital,
        Dependencia,
        Incidencia,
        Incidente,
        Sala,
        Vulnerabilidade,
        Software,
        Alerta,
        Anticorpo,
        Tolerancia,
        SugestaoImune,
        RelacaoAtivos,
        PerimetroRelacoes,
        SensorHoneypot,
    )

    for modelo in (
        Sala,
        Ativo,
        Vulnerabilidade,
        Incidencia,
        Dependencia,
        Incidente,
        CertificadoDigital,
        Software,
        Alerta,
        Anticorpo,
        Tolerancia,
        SugestaoImune,
        RelacaoAtivos,
        PerimetroRelacoes,
        SensorHoneypot,
    ):
        post_save.connect(
            auditar_salvamento,
            sender=modelo,
            weak=False,
            dispatch_uid=f"sauron.auditoria.salvar.{modelo.__name__}",
        )
        post_delete.connect(
            auditar_exclusao,
            sender=modelo,
            weak=False,
            dispatch_uid=f"sauron.auditoria.excluir.{modelo.__name__}",
        )


def auditar_permissoes(sender, instance, action, pk_set, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        registrar_evento("PERMISSOES", type(instance).__name__, instance.pk,
                        {"operacao":action, "ids":sorted(pk_set or [])})


def auditar_login(sender, request, user, **kwargs):
    from inventario.seguranca import ip_cliente
    with usar_usuario(user):
        registrar_evento("LOGIN", "Autenticacao", user.username,
                        {"ip":ip_cliente(request) if request else ""})


def auditar_logout(sender, request, user, **kwargs):
    if user:
        from inventario.seguranca import ip_cliente
        with usar_usuario(user):
            registrar_evento("LOGOUT", "Autenticacao", user.username,
                            {"ip":ip_cliente(request) if request else ""})


def conectar_sinais_autenticacao():
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group
    from django.contrib.auth.signals import user_logged_in, user_logged_out
    from django.db.models.signals import m2m_changed
    User=get_user_model()
    for modelo in (User,Group):
        post_save.connect(auditar_salvamento,sender=modelo,weak=False,dispatch_uid=f"audit.auth.save.{modelo.__name__}")
        post_delete.connect(auditar_exclusao,sender=modelo,weak=False,dispatch_uid=f"audit.auth.delete.{modelo.__name__}")
    for relacao in (User.groups.through,User.user_permissions.through,Group.permissions.through):
        m2m_changed.connect(auditar_permissoes,sender=relacao,weak=False,dispatch_uid=f"audit.m2m.{relacao.__name__}")
    user_logged_in.connect(auditar_login,weak=False,dispatch_uid="audit.login")
    user_logged_out.connect(auditar_logout,weak=False,dispatch_uid="audit.logout")
