"""Diagnóstico local: não testa a internet nem modifica cache, fontes ou inventário."""
import json
from datetime import timedelta

from django.conf import settings
from django.db.models import Count, F, Max, Q
from django.utils import timezone

from inventario.infraestrutura.cve_client import CisaKevClient, IntegracaoCVEError, MAXIMO_DOWNLOAD, NvdClient
from inventario.models import Vulnerabilidade

LIMITE_NVD = 100
LIMITE_BYTES_NVD = 4 * 1024 * 1024


def _rotina_kev():
    caminho = settings.DATA_DIR / "ultima_rotina.json"
    try:
        if caminho.stat().st_size > 1024 * 1024:
            return "Registro da rotina indisponível ou inválido."
        registro = json.loads(caminho.read_text(encoding="utf-8"))
        if not isinstance(registro, dict) or not isinstance(registro.get("erros"), dict):
            return "Registro da rotina indisponível ou inválido."
        if registro["erros"].get("kev"):
            return "A última rotina registrou falha na etapa KEV; confira o diagnóstico da rotina."
        return "A última rotina não registrou falha na etapa KEV; isso não comprova conexão atual."
    except (OSError, ValueError, TypeError):
        return "Sem registro confiável da última rotina; conexão com a fonte desconhecida."


def estado_kev():
    caminho = settings.DATA_DIR / "cache_kev.json"
    rotina = _rotina_kev()
    if not caminho.is_file():
        return {"estado": "Sem cache", "detalhe": "Ainda não há catálogo local.", "rotina": rotina}
    try:
        if caminho.stat().st_size > MAXIMO_DOWNLOAD + 1024:
            raise IntegracaoCVEError("Cache excede o tamanho permitido.")
        dados, origem = CisaKevClient(caminho).carregar()
    except (IntegracaoCVEError, OSError):
        return {"estado": "Cache inválido", "detalhe": "O catálogo local não pôde ser validado.", "rotina": rotina}
    estado = "Desatualizado" if "expirado" in origem else "Atualizado no cache"
    if not dados["vulnerabilities"]:
        estado = "Catálogo vazio (desatualizado)" if estado == "Desatualizado" else "Catálogo vazio"
    return {"estado": estado, "detalhe": origem, "quantidade": len(dados["vulnerabilities"]), "rotina": rotina}


def estado_nvd(qs, total):
    cliente = NvdClient(settings.NVD_API_KEY, settings.DATA_DIR / "cache" / "nvd")
    totais = {"recentes": 0, "antigos": 0, "ausentes": 0, "invalidos": 0, "nao_lidos": 0}
    restante = LIMITE_BYTES_NVD
    ultima = None
    for cve in qs.order_by("cve_id").values_list("cve_id", flat=True)[:LIMITE_NVD]:
        try:
            _, caminho = cliente._caminho(cve)
            if not caminho.is_file():
                totais["ausentes"] += 1
                continue
            tamanho = caminho.stat().st_size
            if tamanho > restante:
                totais["nao_lidos"] += 1
                continue
            restante -= tamanho
            registro = cliente.registro_cache(cve)
        except (IntegracaoCVEError, ValueError, OSError):
            totais["invalidos"] += 1
            continue
        totais["antigos" if registro["expirado"] else "recentes"] += 1
        data = registro["consultado_em"]
        ultima = max(ultima, data) if ultima else data
    return {**totais, "total": total, "examinados": sum(totais.values()), "limite": LIMITE_NVD,
            "ultima": ultima, "parcial": total > LIMITE_NVD or totais["nao_lidos"] > 0}


def estado_epss(qs, total):
    hoje = timezone.now().date()
    coerente = Q(epss__isnull=False, epss_data__isnull=False, epss_observacao__isnull=False,
                 epss_observacao__cve_id=F("cve_id"), epss_observacao__data=F("epss_data"),
                 epss_observacao__epss=F("epss"))
    recente = coerente & Q(epss_data__gte=hoje - timedelta(days=2), epss_data__lte=hoje)
    antigo = coerente & Q(epss_data__lt=hoje - timedelta(days=2))
    futuro = coerente & Q(epss_data__gt=hoje)
    dados = qs.aggregate(recentes=Count("pk", filter=recente), antigos=Count("pk", filter=antigo),
                         futuros=Count("pk", filter=futuro), ultima_coleta=Max("epss_observacao__coletado_em", filter=coerente))
    dados["sem_dados_coerentes"] = total - dados["recentes"] - dados["antigos"] - dados["futuros"]
    dados["total"] = total
    return dados


def resumo_fontes(ver_isca=False):
    qs = Vulnerabilidade.objects.exclude(cve_id__isnull=True).exclude(cve_id="")
    total = qs.count()
    resultado = {"kev": estado_kev(), "nvd": estado_nvd(qs, total), "epss": estado_epss(qs, total)}
    if ver_isca:
        from inventario.models import EventoHoneypot, SensorHoneypot
        resultado["isca"] = {"sensores": SensorHoneypot.objects.count(),
            "habilitados": SensorHoneypot.objects.filter(habilitado=True).count(),
            "eventos": EventoHoneypot.objects.count(),
            "ultimo_recebido": EventoHoneypot.objects.aggregate(valor=Max("recebido_em"))["valor"]}
    return resultado
