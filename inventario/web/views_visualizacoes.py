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
    from inventario.aplicacao.qualidade_dados import qualidade_recorte_risco
    perfil = request.GET.get("perfil", "puro")
    contexto = {
        "perfil": perfil,
        "risco": None,
        "risco_json": {},
        "erro_risco": None,
        "indice_medio": None,
        "qualidade_recorte": qualidade_recorte_risco(request.user),
    }
    try:
        risco = calcular_risco_banco(perfil=perfil)
        contexto.update(risco=risco, risco_json=risco)
        indices = risco["indices"]
        contexto["indice_medio"] = sum(indices) / len(indices) if indices else None
    except ValueError as erro:
        contexto["erro_risco"] = str(erro)
    return contexto


@require_GET
def mapa(request):
    contexto = contexto_risco(request)
    contexto["grafo"] = {}
    if contexto["risco"]:
        from django.db.models import Count, F, Max, Window
        from django.db.models.functions import RowNumber
        ids = contexto['risco']['ids_ativos'][:60]
        ativos = Ativo.objects.filter(pk__in=ids).values('pk', 'hostname', 'tipo', 'criticidade')
        tipos = dict(Ativo._meta.get_field('tipo').choices)
        detalhes = {a['pk']: {'tipo': a['tipo'], 'tipo_nome': tipos.get(a['tipo'], a['tipo']),
                    'criticidade': a['criticidade'], 'cves': [], 'total_cves': 0, 'maior_cvss': None} for a in ativos}
        nomes = {a['pk']: a['hostname'] for a in ativos}
        vinculos = Incidencia.objects.filter(ativo_id__in=ids, status__in=['ABERTA', 'TRATAMENTO', 'ACEITA'])
        for grupo in vinculos.values('ativo_id').annotate(total=Count('pk'), maior=Max('vulnerabilidade__cvss')):
            detalhes[grupo['ativo_id']].update(total_cves=grupo['total'], maior_cvss=grupo['maior'])
        primeiros = vinculos.annotate(posicao=Window(expression=RowNumber(), partition_by=[F('ativo_id')],
            order_by=[F('vulnerabilidade__cvss').desc(), F('pk').asc()])).filter(posicao__lte=3)
        for item in primeiros.values('ativo_id', 'vulnerabilidade_id', 'vulnerabilidade__cve_id', 'vulnerabilidade__cvss'):
            detalhes[item['ativo_id']]['cves'].append({'id': item['vulnerabilidade__cve_id'] or item['vulnerabilidade_id'],
                                                      'cvss': item['vulnerabilidade__cvss']})
        contexto["grafo"] = grafo_dependencias(contexto["risco"], nomes, detalhes)
        contexto['tipos_grafo'] = Ativo._meta.get_field('tipo').choices
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
