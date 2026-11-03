from __future__ import annotations

import json
import logging
from tempfile import NamedTemporaryFile
import time

from django.conf import settings
from django.apps import apps
from django.db import connection, DatabaseError
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET, require_http_methods

from inventario.matematica.cvss import CalculadoraCVSS31
from inventario.infraestrutura.cve_client import CisaKevClient, IntegracaoCVEError, NvdClient
from inventario.models import Ativo
from inventario.aplicacao.risco import (
    analisar_historico_risco,
    calcular_risco_banco,
    caminho_cache_kev,
    simular_correcao,
)


from inventario.web.saude import liveness as api_saude

INICIO_PROCESSO = time.monotonic()
LOGGER = logging.getLogger(__name__)


@require_GET
def api_saude_detalhe(request):
    db = escrita = "ok"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone() != (1,):
                raise DatabaseError("SELECT 1 não retornou o resultado esperado.")
        necessarias = {m._meta.db_table for m in apps.get_app_config('inventario').get_models()
                       if not m._meta.proxy and m._meta.managed}
        necessarias.update({'django_migrations', 'auth_user', 'django_session'})
        if not necessarias.issubset(connection.introspection.table_names()):
            raise DatabaseError('Estrutura do banco incompleta; execute preparar_servidor.')
    except DatabaseError:
        db = "erro"
        LOGGER.exception("Healthcheck: banco indisponível.")
    try:
        # Criar, gravar e apagar confirma permissões reais; os.access seria insuficiente.
        with NamedTemporaryFile(dir=settings.DATA_DIR, prefix=".saude-", mode="w+") as teste:
            teste.write("Sauron")
            teste.flush()
    except OSError:
        escrita = "erro"
        LOGGER.exception("Healthcheck: diretório de dados sem escrita.")
    ultima = None
    estado_rotina = "pendente"
    marcador = settings.DATA_DIR / "ultima_rotina.json"
    if marcador.is_file():
        try:
            rotina = json.loads(marcador.read_text(encoding="utf-8"))
            if not isinstance(rotina, dict):
                raise ValueError('Marcador de rotina inválido.')
            ultima = rotina.get("ultima_rotina_em")
            estado_rotina = rotina.get("status", "desconhecido")
        except (OSError, ValueError):
            LOGGER.warning("Marcador da última rotina inválido.")
    saudavel = db == escrita == "ok"
    uptime = round(time.monotonic() - INICIO_PROCESSO, 2)
    return JsonResponse(
        {
            "status": "ok" if saudavel else "erro",
            "db": db,
            "escrita": escrita,
            "uptime": uptime,
            "ultima_rotina_em": ultima,
            "servico": "Sauron",
            "status_rotina": estado_rotina,
            # Compatibilidade com o shell visual entregue anteriormente.
            "uptime_segundos": uptime,
            "banco": "conectado" if db == "ok" else "indisponivel",
        },
        status=200 if saudavel else 503,
    )


@require_GET
def api_ativos(request):
    dados = list(
        Ativo.objects.values(
            "id",
            "id_numerico",
            "tipo",
            "nome",
            "hostname",
            "fabricante",
            "modelo",
            "ip",
            "responsavel",
            "sala_id",
            "criticidade",
            "status",
        )
    )
    return JsonResponse({"quantidade": len(dados), "ativos": dados})


@require_GET
def api_risco(request):
    try:
        perfil = request.GET.get("perfil")
        return JsonResponse(
            calcular_risco_banco(
                usar_exposicao=request.GET.get("exposicao") == "1",
                perfil=perfil,
            )
        )
    except ValueError as erro:
        return JsonResponse({"erro": str(erro)}, status=422)


@require_http_methods(["POST"])
def api_simular_risco(request):
    try:
        dados = json.loads(request.body)
        if not isinstance(dados, dict):
            raise ValueError("Envie um objeto JSON.")
        ids = dados.get("incidencias_corrigidas")
        if not isinstance(ids, list) or len(ids) > 10000:
            raise ValueError("Envie uma lista de até 10000 IDs em incidencias_corrigidas.")
        return JsonResponse(simular_correcao(ids, perfil=dados.get("perfil", "puro")))
    except (ValueError, TypeError) as erro:
        return JsonResponse({"erro": str(erro)}, status=400)


@require_GET
def api_historico_risco(request):
    try:
        return JsonResponse(
            analisar_historico_risco(
                request.GET.get("inicio") or None,
                request.GET.get("fim") or None,
            )
        )
    except ValueError as erro:
        return JsonResponse({"erro": str(erro)}, status=400)


@require_GET
def api_cvss(request):
    try:
        resultado = CalculadoraCVSS31.calcular(request.GET.get("vetor", ""))
        return JsonResponse(
            {
                "score": resultado.score,
                "severidade": resultado.severidade,
                "impacto": resultado.impacto,
                "explorabilidade": resultado.explorabilidade,
                "vetor": resultado.vetor,
            }
        )
    except ValueError as erro:
        return JsonResponse({"erro": str(erro)}, status=400)


@require_GET
def api_kev(request):
    try:
        limite = int(request.GET.get("limite", "15"))
        offline = request.GET.get("offline") == "1"
        dados = CisaKevClient(caminho_cache_kev()).listar_recentes(
            limite, permitir_rede=not offline
        )
        return JsonResponse(dados)
    except (ValueError, IntegracaoCVEError) as erro:
        return JsonResponse({"erro": str(erro)}, status=503)


@require_GET
def api_nvd(request, cve_id):
    try:
        return JsonResponse(
            NvdClient(settings.NVD_API_KEY, settings.DATA_DIR / "cache" / "nvd").buscar(cve_id)
        )
    except (ValueError, IntegracaoCVEError) as erro:
        return JsonResponse({"erro": str(erro)}, status=503)


@require_GET
def exportar_ativos_csv(request):
    return exportar_colecao_csv(request, "ativos")


@require_GET
def exportar_colecao_csv(request, colecao):
    from inventario.infraestrutura.auditoria import registrar_evento
    from inventario.infraestrutura.relatorios import relatorio_csv

    try:
        texto = relatorio_csv(colecao, request.user)
    except ValueError as erro:
        return HttpResponse(str(erro), status=400)
    registrar_evento("EXPORTAR_CSV", "Inventario", colecao)
    resposta = HttpResponse(texto, content_type="text/csv; charset=utf-8")
    resposta["Content-Disposition"] = f'attachment; filename="{colecao}_sauron.csv"'
    return resposta


@require_GET
def api_verificar_auditoria(request):
    from inventario.infraestrutura.auditoria import verificar_cadeia

    resultado = verificar_cadeia()
    return JsonResponse(resultado, status=200 if resultado["integra"] else 409)


from inventario.web.views_cadastros import (
    listar_ativos,
    detalhe_ativo,
    criar_ativo,
    listar_vulnerabilidades,
    criar_vulnerabilidade,
)
from inventario.web.views_paginas import (
    alertas,
    alterar_status_incidencia,
    auditoria,
    dashboard,
    importar_ativos,
    menu_cves,
    modo_euler,
    reconhecer_alerta_web,
    software,
    status_incidencia_web,
)
