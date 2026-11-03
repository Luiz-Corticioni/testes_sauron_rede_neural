"""Telas somente de leitura protegidas pelas quatro permissões do cálculo."""

from django.shortcuts import render
from django.views.decorators.http import require_GET
from django.db import transaction
from inventario.models import Ativo, Incidencia
from inventario.aplicacao.servicos import calcular_risco_banco
from inventario.web.visualizacao import grafo_dependencias, mapas_calor
from inventario.aplicacao.impacto import analisar_impacto
from inventario.aplicacao.analise_linear import explicar_modelo


def contexto_risco(request):
    perfil = request.GET.get("perfil", "puro")
    contexto = {
        "perfil": perfil,
        "risco": None,
        "risco_json": {},
        "erro_risco": None,
        "indice_medio": 0,
    }
    try:
        risco = calcular_risco_banco(perfil=perfil)
        contexto.update(risco=risco, risco_json=risco)
        indices = risco["indices"]
        contexto["indice_medio"] = sum(indices) / len(indices) if indices else 0
    except ValueError as erro:
        contexto["erro_risco"] = str(erro)
    return contexto


@require_GET
def mapa(request):
    contexto = contexto_risco(request)
    contexto["grafo"] = {}
    if contexto["risco"]:
        nomes = dict(Ativo.objects.values_list("pk", "hostname"))
        contexto["grafo"] = grafo_dependencias(contexto["risco"], nomes)
    contexto.update(termo_impacto=request.GET.get("origem", ""), impacto=None, erro_impacto=None)
    if contexto["termo_impacto"]:
        try:
            contexto["impacto"] = analisar_impacto(contexto["termo_impacto"], request.user)
        except Ativo.DoesNotExist:
            contexto["erro_impacto"] = "Ativo não encontrado. Use o número, código, hostname ou nome exato."
        except ValueError as erro:
            contexto["erro_impacto"] = str(erro)
    return render(request, "inventario/mapa.html", contexto)


@require_GET
@transaction.atomic
def matrizes(request):
    contexto = contexto_risco(request)
    contexto.update(mapas=[], inversa=[], diagnostico=None, erro_diagnostico=None,
                    termo_ativo=request.GET.get("ativo", ""))
    if contexto["risco"]:
        mapas, inversa = mapas_calor(contexto["risco"])
        contexto.update(mapas=mapas, inversa=inversa)
        try:
            contexto["diagnostico"] = explicar_modelo(
                request.user, contexto["termo_ativo"] or None, contexto["perfil"], contexto["risco"]
            )
        except Ativo.DoesNotExist:
            contexto["erro_diagnostico"] = "Ativo não encontrado. Use o número, código, hostname ou nome exato."
        except ValueError as erro:
            contexto["erro_diagnostico"] = str(erro)
    return render(request, "inventario/matrizes.html", contexto)


@require_GET
def prioridades(request):
    contexto = contexto_risco(request)
    grupos = {}
    for id_, vul in Incidencia.objects.filter(
        status__in=["ABERTA", "TRATAMENTO", "ACEITA"]
    ).values_list("pk", "vulnerabilidade_id"):
        grupos.setdefault(vul, []).append(id_)
    contexto["prioridades"] = [
        dict(item, incidencias=",".join(grupos.get(item["vulnerabilidade_id"], [])))
        for item in (contexto["risco"] or {}).get("prioridade_correcao", [])
    ]
    return render(request, "inventario/prioridades.html", contexto)
