"""Consulta de dependentes com os mesmos dados que alimentam A, sem resolver o risco."""

from django.db import transaction

from inventario.aplicacao.consultas import consultar_ativo
from inventario.aplicacao.operacao import exigir
from inventario.dominio.grafo import GrafoDependencias
from inventario.models import Ativo, Dependencia


@transaction.atomic
def analisar_impacto(termo, usuario, limite=50):
    exigir(usuario, "inventario.view_ativo")
    exigir(usuario, "inventario.view_dependencia")
    if not isinstance(termo, str) or not 1 <= len(termo.strip()) <= 100:
        raise ValueError("Informe ID numérico, código, hostname ou nome exato (até 100 caracteres).")
    origem = consultar_ativo(termo)
    identidades = {a.id: {"id": a.id, "id_numerico": a.id_numerico, "hostname": a.hostname}
                   for a in Ativo.objects.only("id", "id_numerico", "hostname")}
    grafo = GrafoDependencias(list(identidades), [d.para_dominio() for d in Dependencia.objects.all()])
    resultado = grafo.alcance(origem.pk, limite)
    resultado["ativo"] = identidades[origem.pk]
    for item in resultado["itens"]:
        item.update(identidades[item["id"]])
        item["caminho_nomes"] = [identidades[c]["hostname"] for c in item["caminho"]]
    return resultado
