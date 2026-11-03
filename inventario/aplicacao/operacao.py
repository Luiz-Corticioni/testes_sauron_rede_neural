"""Serviços operacionais compartilhados pelo terminal, web e agendador."""

from datetime import date, timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from inventario.aplicacao.autorizacao import exigir
from django.db import transaction
from django.utils import timezone

from inventario.infraestrutura.auditoria import travar_escrita, usar_usuario
from inventario.models import (
    Alerta,
    Ativo,
    CertificadoDigital,
    HistoricoIncidencia,
    Incidencia,
    Software,
    Vulnerabilidade,
)


def prazo_sla(incidencia):
    """Prazo interno desde a detecção; o dueDate CISA é informativo e separado."""
    v = incidencia.vulnerabilidade
    from inventario.matematica.cvss import score_ambiental_ativo
    score = score_ambiental_ativo(v, incidencia.ativo)
    categoria = (
        "CRITICA" if score >= 9 else "ALTA" if score >= 7 else "MEDIA" if score >= 4 else "BAIXA"
    )
    dias = settings.SLA_DIAS[categoria]
    if v.kev:
        dias = min(dias, settings.SLA_DIAS["KEV"])
    if type(dias) is not int or not 1 <= dias <= 3650:
        raise ValueError("SLA deve estar entre 1 e 3650 dias.")
    return incidencia.detectada_em + timedelta(days=dias)


@transaction.atomic
def atualizar_prazos():
    travar_escrita()
    quantidade = 0
    for i in Incidencia.objects.pendentes_sla().select_related("vulnerabilidade"):
        prazo = prazo_sla(i)
        if i.prazo_correcao is None or prazo < i.prazo_correcao:
            i.prazo_correcao = prazo
            i.save(update_fields=["prazo_correcao"])
            quantidade += 1
    return quantidade


@transaction.atomic
def emitir_alerta(tipo, ativo, chave, mensagem, severidade=2):
    # O lock vem antes da leitura. Evita dois escritores disputando a mesma lacuna.
    travar_escrita()
    alerta = Alerta.objects.filter(
        tipo=tipo, ativo=ativo, chave=chave, reconhecido_em__isnull=True
    ).first()
    if alerta:
        return alerta
    ultimo = Alerta.objects.filter(tipo=tipo, ativo=ativo, chave=chave,
        reconhecido_em__isnull=False).order_by("-reconhecido_em", "-pk").first()
    if ultimo and ultimo.suprimido_ate and ultimo.suprimido_ate > timezone.now():
        return ultimo
    alerta = Alerta(tipo=tipo, ativo=ativo, chave=chave, mensagem=mensagem, severidade=severidade)
    alerta.full_clean()
    alerta.save()
    return alerta


@transaction.atomic
def reconhecer_alerta(pk, usuario):
    travar_escrita()
    usuario = exigir(usuario, "inventario.reconhecer_alerta")
    alerta = Alerta.objects.get(pk=pk)
    if alerta.reconhecido_em is None:
        with usar_usuario(usuario):
            alerta.reconhecido_por = usuario
            alerta.reconhecido_em = timezone.now()
            alerta.suprimido_ate = alerta.reconhecido_em + timedelta(days=settings.ALERTA_SUPRESSAO_DIAS)
            alerta.save(update_fields=["reconhecido_por", "reconhecido_em", "suprimido_ate"])
    return alerta


@transaction.atomic
def alterar_status(pk, status, usuario, justificativa="", aceita_ate=None, evidencia=""):
    travar_escrita()
    usuario = exigir(usuario, "inventario.change_incidencia")
    if status not in dict(Incidencia.Status.choices):
        raise ValidationError("Status inválido.")
    i = Incidencia.objects.select_related("ativo", "vulnerabilidade").get(pk=pk)
    from inventario.aplicacao.decisoes import preparar_decisao
    with usar_usuario(usuario):
        if i.decisao_pendente != status:
            if status == "ACEITA":
                if isinstance(aceita_ate, str):
                    try:
                        aceita_ate = date.fromisoformat(aceita_ate)
                    except ValueError as erro:
                        raise ValidationError("Use data AAAA-MM-DD.") from erro
                i.justificativa, i.aceita_ate = justificativa, aceita_ate
            if status in ("CORRIGIDA", "MITIGADA"):
                i.evidencia = evidencia
        preparar_decisao(i, status, usuario)
        i.save()
    return i


@transaction.atomic
def decidir_pendencia(pk, aprovar, usuario, motivo=""):
    """Aprova ou devolve a solicitação persistida, sem receber seus termos no POST."""
    travar_escrita()
    usuario = exigir(usuario, "inventario.change_incidencia")
    i = Incidencia.objects.select_related("ativo", "vulnerabilidade").get(pk=pk)
    alvo = i.decisao_pendente
    if not alvo:
        raise ValidationError("Não há decisão pendente para esta incidência.")
    exigir(usuario, "inventario.aprovar_aceite_risco" if alvo == "ACEITA"
           else "inventario.change_incidencia")
    if i.solicitada_por_id == usuario.pk:
        raise ValidationError("Solicitante não pode revisar a própria decisão.")
    if aprovar:
        return alterar_status(pk, alvo, usuario)
    if not motivo.strip() or len(motivo) > 4000:
        raise ValidationError("A devolução exige motivo de até 4000 caracteres.")
    from inventario.infraestrutura.auditoria import registrar_evento
    with usar_usuario(usuario):
        i.decisao_pendente, i.status, i.aprovada_por = "", "TRATAMENTO", None
        i.save()
        registrar_evento("DECISAO_DEVOLVIDA", "Incidencia", pk,
                        {"alvo": alvo, "motivo": motivo, "solicitada_por_id": i.solicitada_por_id})
    return i


@transaction.atomic
def expirar_aceites():
    travar_escrita()
    quantidade = 0
    for i in Incidencia.objects.select_related("ativo", "vulnerabilidade").filter(
        status="ACEITA", aceita_ate__lt=timezone.localdate()
    ):
        i.status = "ABERTA"
        i.save(update_fields=["status"])
        emitir_alerta(
            "ACEITE_VENCIDO",
            i.ativo,
            f"{i.pk}:{i.aceita_ate}",
            f"{i.pk}: aceite venceu em {i.aceita_ate}; risco reaberto.",
            3,
        )
        quantidade += 1
    return quantidade


def alertas_inventario():
    hoje = timezone.localdate()
    for a in Ativo.objects.exclude(status="BAIXADO"):
        if not a.responsavel.strip() or not a.contato.strip():
            emitir_alerta("SEM_DONO", a, "custodiante", "Defina responsável e e-mail de contato.")
        if a.fim_suporte and a.fim_suporte <= hoje + timedelta(days=settings.ALERTA_EOL_DIAS):
            emitir_alerta(
                "EOL",
                a,
                str(a.fim_suporte),
                f"Suporte termina/terminou em {a.fim_suporte}.",
                3 if a.fim_suporte < hoje else 2,
            )
    for c in CertificadoDigital.objects.select_related("ativo").filter(
        expira_em__lte=hoje + timedelta(days=settings.ALERTA_CERT_DIAS)
    ):
        emitir_alerta(
            "CERT",
            c.ativo,
            f"{c.pk}:{c.expira_em}",
            f"Certificado {c.dominio}: expiração em {c.expira_em}.",
            3 if c.expira_em < hoje else 2,
        )
    for i in (
        Incidencia.objects.pendentes_sla().select_related("ativo").filter(prazo_correcao__lt=hoje)
    ):
        emitir_alerta(
            "SLA",
            i.ativo,
            f"{i.pk}:{i.prazo_correcao}",
            f"SLA_VENCIDO: {i.pk}, prazo {i.prazo_correcao}.",
            3,
        )


@transaction.atomic
def enriquecer_kev(dados):
    from inventario.infraestrutura.cve_client import validar_kev

    validar_kev(dados)
    itens = {item["cveID"]: item for item in dados["vulnerabilities"]}
    travar_escrita()
    alteradas = 0
    for v in Vulnerabilidade.objects.filter(cve_id__in=itens):
        item = itens[v.cve_id]
        campos = {
            "kev": True,
            "kev_adicionada_em": date.fromisoformat(item["dateAdded"]),
            "kev_prazo": date.fromisoformat(item["dueDate"]),
            "uso_ransomware": item.get("knownRansomwareCampaignUse", "Unknown"),
        }
        entrou = not v.kev
        if any(getattr(v, nome) != valor for nome, valor in campos.items()):
            for nome, valor in campos.items():
                setattr(v, nome, valor)
            v.save(update_fields=list(campos))
            alteradas += 1
        if entrou and not Incidencia.objects.filter(vulnerabilidade=v).exists():
            emitir_alerta(
                "KEV",
                None,
                f"{v.pk}:{v.kev_adicionada_em}",
                f"{v.cve_id} consta no KEV; ainda sem ativos vinculados.",
                4,
            )
        for i in Incidencia.objects.select_related("ativo").filter(vulnerabilidade=v):
            if entrou:
                emitir_alerta(
                    "KEV",
                    i.ativo,
                    f"{v.pk}:{v.kev_adicionada_em}",
                    f"{v.cve_id} consta no catálogo KEV: exploração conhecida.",
                    4,
                )
            if i.status in {"ABERTA", "TRATAMENTO"}:
                i.vulnerabilidade = v
                prazo = prazo_sla(i)
                if i.prazo_correcao is None or prazo < i.prazo_correcao:
                    i.prazo_correcao = prazo
                    i.save(update_fields=["prazo_correcao"])
    return alteradas


def calcular_mttr():
    """Média de ciclos abertura→CORRIGIDA; MITIGADA não é correção comprovada."""
    aberturas, duracoes = {}, []
    for h in HistoricoIncidencia.objects.order_by("em", "id"):
        if h.para in {"ABERTA", "TRATAMENTO", "ACEITA"}:
            aberturas.setdefault(h.incidencia_codigo, h.em)
        elif h.para == "CORRIGIDA":
            inicio = aberturas.pop(h.incidencia_codigo, None)
            if inicio:
                duracoes.append((h.em - inicio).total_seconds() / 86400)
        elif h.para == "MITIGADA":
            aberturas.pop(h.incidencia_codigo, None)
    return {
        "dias": round(sum(duracoes) / len(duracoes), 3) if duracoes else None,
        "correcoes": len(duracoes),
    }


def alertar_tendencia():
    from inventario.aplicacao.risco import analisar_historico_risco

    resultado = analisar_historico_risco()
    if resultado.get("disponivel") and resultado.get("alertas"):
        # A chave representa a última amostra, evitando alertas repetidos por hora.
        from inventario.models import SnapshotRisco

        ultimo = SnapshotRisco.objects.order_by("ts", "pk").last()
        for aviso in resultado["alertas"]:
            emitir_alerta("TENDENCIA", None, f"snapshot:{ultimo.pk}", aviso["mensagem"], 3)
    return resultado


from inventario.aplicacao.operacao_cves import cvss_nvd, registrar_sugestao, sugerir_cves
