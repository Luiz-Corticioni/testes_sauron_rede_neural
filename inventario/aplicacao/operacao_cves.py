"""Sugestões NVD por CPE: serviços de integração separados dos prazos e decisões."""

from datetime import date, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from inventario.infraestrutura.auditoria import travar_escrita
from inventario.models import Incidencia, Software, Vulnerabilidade


def cvss_nvd(cve):
    """Seleciona 3.1/3.0/4.0 com a mesma política da consulta e do comparador."""
    from inventario.dominio.comparacao_cvss import selecionar_metrica
    for versao in ("3.1", "3.0", "4.0"):
        metrica=selecionar_metrica(cve,versao)
        if metrica["nota"] is not None:
            return metrica["nota"], versao, metrica["vetor"]
    return None


def metrica_v4(cve):
    from inventario.dominio.comparacao_cvss import selecionar_metrica
    metrica=selecionar_metrica(cve,"4.0")
    if metrica["nota"] is None:
        return {}
    return {"baseScore":metrica["nota"], "vectorString":metrica["vetor"], "version":"4.0",
            "fonte":metrica["publicador"], "origem":"NVD", "tipo":metrica["tipo"],
            "registro_alterado_em":cve.get("lastModified", "")}


def elegivel(cve):
    if cve.get("vulnStatus") == "Rejected":
        return False
    score = cvss_nvd(cve)
    try:
        recente = date.fromisoformat(cve.get("published", "")[:10]) >= timezone.localdate()-timedelta(days=3*365)
    except ValueError:
        recente = False
    return bool((score and score[0] >= settings.NVD_CVSS_MINIMO) or cve.get("cisaExploitAdd")
                or Vulnerabilidade.objects.filter(cve_id=cve["id"], kev=True).exists() or recente)


@transaction.atomic
def registrar_sugestao(software, cve):
    if not elegivel(cve):
        return False
    from inventario.dominio.matching import extrair_faixas
    travar_escrita()
    v = Vulnerabilidade.objects.filter(cve_id=cve["id"]).first()
    if not v:
        score = cvss_nvd(cve)
        if score is None:
            return False
        from inventario.aplicacao.cadastros import proximo_id_vulnerabilidade
        codigo = proximo_id_vulnerabilidade("OUTRA")
        descricoes = cve.get("descriptions", [])
        descricao = next((d["value"] for d in descricoes if d.get("lang") == "en"), cve["id"])
        v = Vulnerabilidade.objects.create(
            id=codigo,
            cve_id=cve["id"],
            descricao=descricao,
            cvss=score[0],
            cvss_versao=score[1],
            cvss_vetor=score[2],
            fonte="NVD por CPE",
            faixas_afetadas=extrair_faixas(cve),
            cvss_v4=metrica_v4(cve),
            confianca_nvd="BAIXA" if cve.get("vulnStatus") == "Awaiting Analysis" else "NORMAL",
            publicada_em=cve.get("published", "")[:10] or None,
        )
    faixas = extrair_faixas(cve)
    if faixas and v.faixas_afetadas != faixas:
        v.faixas_afetadas = faixas
        v.save(update_fields=["faixas_afetadas"])
    if Incidencia.objects.filter(ativo=software.ativo, vulnerabilidade=v).exists():
        return False  # Nunca reabre uma rejeitada/corrigida ou altera um vínculo confirmado.
    import uuid

    Incidencia.objects.create(
        id=f"INC-{uuid.uuid4().hex[:24].upper()}",
        ativo=software.ativo,
        vulnerabilidade=v,
        software=software,
        status="SUGERIDA",
        versao_afetada=software.versao,
        observacoes=f"Sugestão NVD ({v.confianca_nvd}) para {software.cpe23}. Confirmar aplicabilidade/configuração.",
    )
    return True


def sugerir_cves(sem_rede=False):
    from inventario.infraestrutura.cve_client import IntegracaoCVEError, NvdClient

    cliente = NvdClient(settings.NVD_API_KEY, settings.DATA_DIR / "cache" / "nvd")
    total, avisos = 0, []
    respostas = {}
    for s in Software.objects.select_related("ativo").exclude(cpe23=""):
        try:
            if s.cpe23 not in respostas:
                respostas[s.cpe23] = cliente.consultar_cpe(s.cpe23, sem_rede=sem_rede)
            resposta = respostas[s.cpe23]
            candidatos = sorted((c for c in resposta["cves"] if elegivel(c)),
                key=lambda c: (bool(c.get("cisaExploitAdd")), (cvss_nvd(c) or (0,))[0],
                               c.get("published", "")), reverse=True)
            if len(candidatos) > settings.NVD_MAX_SUGESTOES_CPE:
                avisos.append(f"{s.nome}: sugestões limitadas a {settings.NVD_MAX_SUGESTOES_CPE}.")
            for cve in candidatos[:settings.NVD_MAX_SUGESTOES_CPE]:
                total += registrar_sugestao(s, cve)
                if (
                    cvss_nvd(cve) is None
                    and not Vulnerabilidade.objects.filter(cve_id=cve["id"]).exists()
                ):
                    avisos.append(f"{cve['id']}: sem CVSS 3.x/4.0; revisão manual necessária.")
            if resposta["truncado"]:
                avisos.append(
                    f"{s.nome}: resultado parcial ({len(resposta['cves'])}/"
                    f"{resposta['total']}); limite de paginação atingido."
                )
        except IntegracaoCVEError as erro:
            avisos.append(f"{s.nome}: {erro}")
    return {"sugeridas": total, "avisos": sorted(set(avisos))}
