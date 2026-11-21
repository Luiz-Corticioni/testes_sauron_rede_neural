"""Credenciais de leitura para integração; o segredo é entregue uma única vez."""
from datetime import timedelta
import hashlib
import hmac
import secrets
import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator, EmptyPage
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from inventario.aplicacao.autorizacao import exigir
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import CredencialAPI, LimiteOrigemAPI

ESCOPO_PERMISSOES = {
    "ativos": ("inventario.view_ativo",),
    "risco": ("inventario.view_ativo", "inventario.view_vulnerabilidade", "inventario.view_incidencia", "inventario.view_dependencia"),
    "incidencias": ("inventario.view_ativo", "inventario.view_vulnerabilidade", "inventario.view_incidencia"),
}
LIMITE_POR_MINUTO = 60
LIMITE_ORIGEM_POR_MINUTO = 120


class CredencialInvalida(Exception):
    pass


class LimiteCredencial(Exception):
    pass


@transaction.atomic
def limitar_origem(origem):
    """Limita também tokens inválidos; a chave não guarda o endereço em claro."""
    chave = hmac.new(settings.SAURON_AUDIT_HMAC_KEY.encode(), b"api-origem:" + origem.encode(), hashlib.sha256).hexdigest()
    agora = timezone.now()
    travar_escrita()
    LimiteOrigemAPI.objects.filter(expira_em__lte=agora).delete()
    registro, _ = LimiteOrigemAPI.objects.get_or_create(chave=chave,
        defaults={"expira_em": agora + timedelta(minutes=1)})
    if registro.quantidade >= LIMITE_ORIGEM_POR_MINUTO:
        return False
    registro.quantidade += 1
    registro.save(update_fields=["quantidade"])
    return True


def _administrador(usuario):
    atual = exigir(usuario, "inventario.view_ativo")
    if not atual.is_superuser:
        raise PermissionDenied("Somente administradores podem gerenciar credenciais de integração.")
    return atual


def _parametros(escopos, dias):
    if (not isinstance(escopos, list) or not escopos or len(escopos) > len(ESCOPO_PERMISSOES)
            or any(not isinstance(item, str) or item not in ESCOPO_PERMISSOES for item in escopos)
            or len(set(escopos)) != len(escopos)):
        raise ValidationError("Selecione escopos de leitura válidos, sem repetições.")
    if type(dias) is not int or not 1 <= dias <= 90:
        raise ValidationError("A validade deve ser de 1 a 90 dias.")
    return sorted(escopos)


def _nova(usuario, escopos, dias):
    identificador = uuid.uuid4()
    segredo = f"sauron_{identificador.hex}.{secrets.token_urlsafe(32)}"
    credencial = CredencialAPI.objects.create(id=identificador, dono=usuario, escopos=escopos,
        segredo_hash=hashlib.sha256(segredo.encode()).hexdigest(), expira_em=timezone.now() + timedelta(days=dias))
    registrar_evento("CREDENCIAL_API_CRIADA", "CredencialAPI", credencial.pk,
                     {"escopos": escopos, "expira_em": credencial.expira_em.isoformat()})
    return credencial, segredo


def listar(usuario, pagina):
    usuario = _administrador(usuario)
    try:
        pagina = int(pagina)
        if pagina < 1:
            raise ValueError
    except (ValueError, TypeError) as erro:
        raise ValidationError("Página deve ser um inteiro positivo.") from erro
    dados = CredencialAPI.objects.filter(dono=usuario).order_by("-criada_em", "id").values(
        "id", "escopos", "criada_em", "expira_em", "revogada_em")
    paginador = Paginator(dados, 50)
    try:
        parte = paginador.page(pagina)
    except EmptyPage as erro:
        raise CredencialInvalida from erro
    return {"pagina": pagina, "paginas": paginador.num_pages, "total": paginador.count,
            "credenciais": list(parte.object_list)}


@transaction.atomic
def criar(usuario, escopos, dias):
    travar_escrita()
    usuario = _administrador(usuario)
    escopos = _parametros(escopos, dias)
    with usar_usuario(usuario):
        return _nova(usuario, escopos, dias)


@transaction.atomic
def revogar(usuario, identificador):
    travar_escrita()
    usuario = _administrador(usuario)
    credencial = CredencialAPI.objects.filter(pk=identificador, dono=usuario).first()
    if credencial is None:
        raise CredencialInvalida
    if credencial.revogada_em is None:
        credencial.revogada_em = timezone.now()
        credencial.save(update_fields=["revogada_em"])
        with usar_usuario(usuario):
            registrar_evento("CREDENCIAL_API_REVOGADA", "CredencialAPI", credencial.pk)
    return credencial


@transaction.atomic
def rotacionar(usuario, identificador, dias):
    travar_escrita()
    usuario = _administrador(usuario)
    anterior = CredencialAPI.objects.filter(pk=identificador, dono=usuario, revogada_em__isnull=True,
                                            expira_em__gt=timezone.now()).first()
    if anterior is None:
        raise CredencialInvalida
    escopos = _parametros(anterior.escopos, dias)
    with usar_usuario(usuario):
        anterior.revogada_em = timezone.now()
        anterior.save(update_fields=["revogada_em"])
        registrar_evento("CREDENCIAL_API_REVOGADA", "CredencialAPI", anterior.pk, {"motivo": "rotacao"})
        return _nova(usuario, escopos, dias)


@transaction.atomic
def autenticar(segredo, escopo):
    if not isinstance(segredo, str) or len(segredo) > 128 or not segredo.startswith("sauron_"):
        raise CredencialInvalida
    try:
        identificador = uuid.UUID(hex=segredo[7:39])
        if segredo[39:40] != ".":
            raise ValueError
    except ValueError as erro:
        raise CredencialInvalida from erro
    hash_recebido = hashlib.sha256(segredo.encode()).hexdigest()
    travar_escrita()
    credencial = CredencialAPI.objects.select_related("dono").filter(pk=identificador).first()
    agora = timezone.now()
    if (credencial is None or not hmac.compare_digest(credencial.segredo_hash, hash_recebido)
            or credencial.revogada_em is not None or credencial.expira_em <= agora
            or not credencial.dono.is_active or not credencial.dono.is_superuser):
        raise CredencialInvalida
    if escopo not in ESCOPO_PERMISSOES or escopo not in credencial.escopos:
        raise PermissionDenied("A credencial não possui o escopo solicitado.")
    if not credencial.dono.has_perms(ESCOPO_PERMISSOES[escopo]):
        raise PermissionDenied("A conta perdeu a permissão necessária.")
    if credencial.janela_em is None or agora >= credencial.janela_em + timedelta(minutes=1):
        credencial.janela_em, credencial.requisicoes_janela = agora, 0
    if credencial.requisicoes_janela >= LIMITE_POR_MINUTO:
        raise LimiteCredencial
    credencial.requisicoes_janela += 1
    credencial.save(update_fields=["janela_em", "requisicoes_janela"])
    with usar_usuario(credencial.dono):
        registrar_evento("CREDENCIAL_API_USADA", "CredencialAPI", credencial.pk, {"escopo": escopo})
    return credencial.dono
