"""Consulta explícita, lote atômico e histórico idempotente; GET nunca usa rede."""
from datetime import date
import hashlib
import json
from django.db import transaction
from django.utils import timezone
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita
from inventario.infraestrutura.cve_client import EpssClient, IntegracaoCVEError
from inventario.models import ObservacaoEPSS, Vulnerabilidade
from inventario.aplicacao.autorizacao import exigir


def sincronizar_epss(usuario=None, limite=None):
    if usuario is not None:
        usuario = exigir(usuario, "inventario.view_vulnerabilidade", "inventario.change_vulnerabilidade")
    if limite is not None and (type(limite) is not int or not 1 <= limite <= 50):
        raise ValueError("Atualização interativa aceita de 1 a 50 CVEs por execução.")
    qs = Vulnerabilidade.objects.exclude(cve_id__isnull=True).exclude(cve_id="").order_by("epss_data", "pk")
    total = qs.count()
    cves = list((qs[:limite] if limite else qs).values_list("cve_id", flat=True))
    resultado = {"atualizadas": 0, "nao_atualizadas": 0, "observacoes_novas": 0, "avisos": []}
    cliente = EpssClient()
    for inicio in range(0, len(cves), 50):  # Respeita também o limite de caracteres da API.
        lote = cves[inicio:inicio + 50]
        try:
            encontrados = cliente.buscar(lote)
        except IntegracaoCVEError as erro:
            resultado["avisos"].append(str(erro))
            break
        with transaction.atomic():
            travar_escrita()
            alterou_inventario = False
            if usuario is not None:
                usuario = exigir(usuario, "inventario.view_vulnerabilidade", "inventario.change_vulnerabilidade")
            for cve, dados in encontrados.items():
                v = Vulnerabilidade.objects.select_for_update().filter(cve_id=cve).first()
                if v is None:
                    continue  # Cadastro pode ter mudado durante a consulta externa.
                assinatura = hashlib.sha256(json.dumps(dados, sort_keys=True, allow_nan=False).encode()).hexdigest()
                observacao, nova = ObservacaoEPSS.objects.get_or_create(cve_id=cve, data=dados["data"], assinatura=assinatura,
                    defaults={"epss": dados["epss"], "percentil": dados["percentil"], "modelo": dados["modelo"]})
                resultado["observacoes_novas"] += int(nova)
                if v.epss_data is None or date.fromisoformat(dados["data"]) >= v.epss_data:
                    mudou = (v.epss, v.epss_data, v.epss_observacao_id) != (dados["epss"], date.fromisoformat(dados["data"]), observacao.pk)
                    if mudou:
                        Vulnerabilidade.objects.filter(pk=v.pk).update(epss=dados["epss"], epss_data=dados["data"], epss_observacao=observacao, atualizado_em=timezone.now())
                        alterou_inventario = True
                        resultado["atualizadas"] += 1
            if alterou_inventario:
                from inventario.aplicacao.servicos import incrementar_versao_inventario
                incrementar_versao_inventario()
            if encontrados:
                registrar_evento("EPSS_SINCRONIZADO", "Inteligencia", "FIRST", {"cves_recebidas": len(encontrados), "observacoes_novas": resultado["observacoes_novas"]})
        ausentes = len(set(lote) - encontrados.keys())
        if ausentes:
            resultado["avisos"].append(f"FIRST não retornou {ausentes} CVE(s) do lote; dados anteriores preservados.")
    resultado["nao_atualizadas"] = len(cves) - resultado["atualizadas"]
    resultado["cves_no_catalogo"], resultado["cves_consultadas"] = total, len(cves)
    if limite and total > limite:
        resultado["avisos"].append("Execução limitada a 50 CVEs com datas mais antigas/ausentes. Para catálogos grandes, agende sync_epss no servidor.")
    return resultado


def situacao_epss(v):
    if v.epss is None or v.epss_data is None:
        return "Sem dados completos"
    if v.epss_data > timezone.now().date():
        return "Data futura inválida"
    return "Desatualizado" if (timezone.now().date() - v.epss_data).days > 2 else "Atualizado"
