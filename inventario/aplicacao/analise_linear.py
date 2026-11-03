"""Explicação calculada a partir do mesmo inventário, compartilhada por CLI e web."""

from django.db import transaction

from inventario.aplicacao.consultas import consultar_ativo
from inventario.aplicacao.operacao import exigir
from inventario.aplicacao.risco import calcular_risco_banco
from inventario.dominio.equipamentos import Equipamento
from inventario.matematica.diagnostico import DiagnosticoLinear
from inventario.models import Ativo


@transaction.atomic
def explicar_modelo(usuario, termo=None, perfil="puro", risco=None):
    for permissao in ("view_ativo", "view_vulnerabilidade", "view_incidencia", "view_dependencia"):
        exigir(usuario, f"inventario.{permissao}")
    if termo is not None and (not isinstance(termo, str) or not 1 <= len(termo.strip()) <= 100):
        raise ValueError("Informe número, código ou hostname de até 100 caracteres.")
    ativo = consultar_ativo(termo) if termo is not None else Ativo.objects.first()
    risco = risco if risco is not None else calcular_risco_banco(perfil=perfil)
    if risco["perfil"] != perfil:
        raise ValueError("O perfil solicitado difere do resultado apresentado.")
    resultado = DiagnosticoLinear.analisar(risco, ativo.pk if ativo else None)
    resultado["perfil"] = perfil
    # Uma única interface, vários comportamentos concretos, sem if por subtipo.
    objetos = [a.para_dominio() for a in Ativo.objects.all()[:12]]
    resultado["objetos"] = [
        {"id": obj.id, "classe": type(obj).__name__, "equipamento": isinstance(obj, Equipamento),
         "detalhes": obj.exibir_detalhes(), "fator_exposicao": obj.fator_exposicao()}
        for obj in objetos
    ]
    resultado["amostra_limitada"] = len(risco["ids_ativos"]) > len(objetos)
    if ativo:
        resultado["hostname"] = ativo.hostname
    return resultado
