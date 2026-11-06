"""Demonstra algoritmos sobre o inventário real, sem modificar o banco."""

import json

from django.core.management.base import BaseCommand

from inventario.aplicacao.risco import carregar_modelo_risco
from inventario.dominio.algoritmos_sprint import dfs_ciclos, merge_sort
from inventario.dominio.grafo import GrafoDependencias
from inventario.models import Ativo


class Command(BaseCommand):
    help = "Mostra ranking de risco puro e alcance estrutural de ativos expostos."

    def handle(self, *args, **options):
        modelo, _ = carregar_modelo_risco("puro")
        resultado = modelo.calcular(perfil="puro")
        ranking = merge_sort(
            [{"id": chave, "risco": risco} for chave, risco in
             zip(resultado.ids_ativos, resultado.risco_efetivo)],
            chave=lambda item: (-item["risco"], item["id"]),
        )
        grafo = GrafoDependencias(modelo.ids_ativos, modelo.dependencias)
        expostos = Ativo.objects.filter(exposto_internet=True).values_list("pk", flat=True)
        alcance = []
        for origem in expostos:
            visitados, ciclo = dfs_ciclos(grafo.vizinhos, origem)
            alcance.append({"origem": origem, "alcancaveis": visitados, "ciclo_alcancavel": ciclo})
        self.stdout.write(json.dumps({"ranking": ranking, "alcance_estrutural": alcance}, ensure_ascii=False, indent=2))
