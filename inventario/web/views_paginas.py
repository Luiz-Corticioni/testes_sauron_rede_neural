from __future__ import annotations

import logging
import time

from django.http import HttpRequest, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from inventario.matematica.euler import Derivador, FuncaoMatematica, Integrador
from inventario.models import (
    Ativo,
    RegistroAuditoria,
)
from inventario.aplicacao.servicos import analisar_historico_risco


INICIO_PROCESSO = time.monotonic()
LOGGER = logging.getLogger(__name__)


def dashboard(request: HttpRequest):
    from inventario.aplicacao.painel import contexto_painel
    try:
        contexto = contexto_painel(request.GET.get("perfil", "puro"),
            ver_alertas=request.user.has_perm("inventario.view_alerta"),
            ver_certificados=request.user.has_perm("inventario.view_certificadodigital"))
    except ValueError as erro:
        return HttpResponseBadRequest(str(erro), content_type='text/plain; charset=utf-8')
    return render(request, "inventario/dashboard.html", contexto)


@require_http_methods(["GET", "POST"])
def modo_euler(request):
    resultado = erro = None
    dados = request.POST if request.method == "POST" else request.GET
    if dados.get("expressao"):
        try:
            funcao = FuncaoMatematica(dados["expressao"])
            operacao = dados.get("operacao", "derivada")
            if operacao not in {'derivada', 'segunda', 'integral'}:
                raise ValueError('Escolha derivada, segunda ou integral.')
            if operacao == "derivada":
                x = float(dados.get("x", 0))
                resultado = {
                    "operacao": "Derivada central",
                    "valor": Derivador.central(funcao.avaliar, x),
                    "em": x,
                }
            elif operacao == "segunda":
                x = float(dados.get("x", 0))
                resultado = {
                    "operacao": "Derivada segunda",
                    "valor": Derivador.segunda(funcao.avaliar, x),
                    "em": x,
                }
            else:
                a, b = float(dados.get("a", 0)), float(dados.get("b", 1))
                n = int(dados.get("n", 100))
                resultado = {
                    "operacao": "Integral de Simpson",
                    "valor": Integrador.simpson(funcao.avaliar, a, b, n),
                    "intervalo": [a, b],
                }
            resultado["tipo_funcao"] = funcao.identificar_tipo()
        except (ValueError, SyntaxError, ZeroDivisionError, OverflowError) as exc:
            erro = str(exc)
    try:
        historico = analisar_historico_risco(dados.get("inicio") or None, dados.get("fim") or None)
    except ValueError as exc:
        historico = {"disponivel": False, "mensagem": str(exc)}
    return render(
        request,
        "inventario/euler.html",
        {
            "resultado": resultado,
            "erro": erro,
            "dados": dados,
            "historico": historico,
        },
    )


def menu_cves(request):
    contexto = {}
    if request.GET.get("ativo"):
        from inventario.aplicacao.operacao import exigir

        exigir(request.user, "inventario.view_ativo")
        contexto["ativo_contexto"] = get_object_or_404(Ativo, pk=request.GET["ativo"])
    return render(request, "inventario/cves.html", contexto)


def auditoria(request):
    return render(
        request,
        "inventario/auditoria.html",
        {
            "registros": RegistroAuditoria.objects.select_related("usuario")[:100],
        },
    )


from inventario.web.views_operacionais import (
    alertas,
    alterar_status_incidencia,
    importar_ativos,
    reconhecer_alerta_web,
    software,
    status_incidencia_web,
)
