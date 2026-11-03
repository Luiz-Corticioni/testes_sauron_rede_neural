"""Regras comuns para decisões humanas, usadas pelos serviços e models."""
from datetime import date, timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone


def alta_severidade(i):
    return i.ativo.criticidade >= 3 or i.vulnerabilidade.cvss >= 9 or i.vulnerabilidade.kev


def validar_validade(valor, dias, campo):
    hoje = timezone.localdate()
    if not isinstance(valor, date) or valor < hoje or valor > hoje + timedelta(days=dias):
        raise ValidationError({campo: f"Validade deve estar entre hoje e {dias} dias."})


def validar_decisao(i):
    if i.status == "ACEITA" or i.decisao_pendente == "ACEITA":
        dias = settings.SAURON_ACEITE_MAX_DIAS if alta_severidade(i) else settings.SAURON_ACEITE_NORMAL_MAX_DIAS
        validar_validade(i.aceita_ate, dias, "aceita_ate")
        if not i.aceita_por_id or not i.justificativa.strip():
            raise ValidationError("Aceite exige autor, prazo e justificativa.")
        if i.status == "ACEITA" and alta_severidade(i):
            validar_segundo(i, "inventario.aprovar_aceite_risco", i.aceita_por_id)
    if i.status in ("CORRIGIDA", "MITIGADA") or i.decisao_pendente in ("CORRIGIDA", "MITIGADA"):
        if not i.evidencia.strip():
            raise ValidationError({"evidencia": "Informe evidência da correção/mitigação."})
        if i.status in ("CORRIGIDA", "MITIGADA") and (i.vulnerabilidade.cvss >= 7 or i.vulnerabilidade.kev):
            validar_segundo(i, "inventario.change_incidencia", i.solicitada_por_id)


def validar_segundo(i, permissao, primeiro):
    from django.contrib.auth import get_user_model
    aprovador = get_user_model().objects.filter(pk=i.aprovada_por_id, is_active=True).first()
    if (not primeiro or not i.aprovada_por_id or i.aprovada_por_id == primeiro
            or aprovador is None or not aprovador.has_perm(permissao)):
        raise ValidationError("Decisão exige segundo usuário distinto com permissão específica.")


def preparar_decisao(i, alvo, usuario):
    from inventario.aplicacao.operacao import exigir
    if alvo not in ("ACEITA", "CORRIGIDA", "MITIGADA"):
        i.status, i.decisao_pendente = alvo, ""
        return
    dupla = alta_severidade(i) if alvo == "ACEITA" else (i.vulnerabilidade.cvss >= 7 or i.vulnerabilidade.kev)
    if i.decisao_pendente == alvo:
        exigir(usuario, "inventario.aprovar_aceite_risco" if alvo == "ACEITA" else "inventario.change_incidencia")
        if i.solicitada_por_id == usuario.pk:
            raise ValidationError("Solicitante não pode aprovar a própria decisão.")
        i.aprovada_por = usuario
        i.status, i.decisao_pendente = alvo, ""
    else:
        if alvo == "ACEITA":
            exigir(usuario, "inventario.aceitar_risco")
            i.aceita_por = usuario
        i.solicitada_por, i.aprovada_por = usuario, None
        i.status, i.decisao_pendente = ("TRATAMENTO", alvo) if dupla else (alvo, "")



def preparar_formulario(instance,dados,usuario):
    """Prepara decisão antes do ModelForm._post_clean sem sobrescrever o primeiro autor."""
    alvo=dados.get("status")
    if alvo not in ("ACEITA","CORRIGIDA","MITIGADA"):
        return dados
    for campo in ("ativo","vulnerabilidade"):
        if campo in dados:
            setattr(instance,campo,dados[campo])
    pendente=instance.decisao_pendente==alvo
    for campo in ("justificativa","aceita_ate","evidencia"):
        if pendente:
            dados[campo]=getattr(instance,campo)
        elif campo in dados:
            setattr(instance,campo,dados[campo])
    anterior = type(instance).objects.filter(pk=instance.pk).first() if instance.pk else None
    if anterior and anterior.status == alvo and not mudanca_material(instance, anterior, alvo):
        return dados
    preparar_decisao(instance,alvo,usuario)
    dados["status"]=instance.status
    instance._decisao_preparada=True
    return dados

def mudanca_material(atual, anterior, alvo):
    """Evidência/componente e termos aprovados não podem herdar assinaturas antigas."""
    campos = ("software_id", "evidencia") if alvo in ("CORRIGIDA", "MITIGADA") else (
        "software_id", "justificativa", "aceita_ate")
    return any(getattr(atual, campo) != getattr(anterior, campo) for campo in campos)
