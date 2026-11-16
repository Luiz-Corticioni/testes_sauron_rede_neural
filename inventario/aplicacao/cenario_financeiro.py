"""Cadastro e simulação de cenário de perda com autorização explícita."""
from copy import copy
from decimal import Decimal
from django.db import transaction

from inventario.aplicacao.autorizacao import exigir
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.infraestrutura.limite_simulacoes import vaga_simulacao
from inventario.matematica.cenario_financeiro import simular_interrupcao
from inventario.matematica.montecarlo import numero


@transaction.atomic
def criar_cenario(cenario, usuario):
    travar_escrita()
    usuario = exigir(usuario, "inventario.view_ativo", "inventario.view_cenariofinanceiro", "inventario.add_cenariofinanceiro")
    cenario.criado_por = usuario
    cenario.full_clean()
    with usar_usuario(usuario):
        cenario.save()
        registrar_evento("CRIAR", "CenarioFinanceiro", cenario.pk, {"ativo": cenario.ativo_id})
    return cenario


def calcular_cenario(cenario, usuario, n=20000, seed=42, limite=None):
    exigir(usuario, "inventario.view_ativo", "inventario.view_cenariofinanceiro")
    cenario.full_clean()
    with vaga_simulacao():
        return simular_interrupcao(cenario, n=n, seed=seed, limite=limite)


def calcular_compartilhado(cenario, usuario, escopo, impactos, sem_sobreposicao, n=20000, seed=42, limite=None):
    """Uma causa comum afeta todos os serviços selecionados pelo mesmo período."""
    from inventario.aplicacao.relacoes import analisar_relacoes
    exigir(usuario, "inventario.view_ativo", "inventario.view_cenariofinanceiro", "inventario.view_relacaoativos")
    cenario.full_clean()
    if sem_sobreposicao is not True:
        raise ValueError("Confirme que os custos são incrementais e não se sobrepõem.")
    if not isinstance(impactos, list) or not 1 <= len(impactos) <= 10:
        raise ValueError("Informe de um a dez serviços dependentes.")
    grafo = analisar_relacoes(usuario, tipo="NEGOCIO", escopo=escopo, origem=cenario.ativo_id, limite=100)
    if grafo["limitado"]:
        raise ValueError("O recorte ultrapassa 100 serviços; restrinja o perímetro antes de simular.")
    permitidos = {item["id"] for item in grafo["itens"]}
    vistos, custos, adicionais = set(), Decimal(cenario.custo_hora), Decimal(cenario.custo_adicional)
    for item in impactos:
        if not isinstance(item, dict) or set(item) != {"ativo_id", "custo_hora", "custo_adicional", "justificativa"}:
            raise ValueError("Informe ativo, custos e justificativa de cada serviço.")
        identificador = item["ativo_id"]
        justificativa = item["justificativa"]
        if not isinstance(identificador, str) or identificador not in permitidos or identificador in vistos:
            raise ValueError("Serviço repetido ou fora do alcance elegível no escopo informado.")
        if not isinstance(justificativa, str) or not justificativa.strip() or len(justificativa) > 300:
            raise ValueError("Informe a origem ou justificativa de cada custo, com até 300 caracteres.")
        for chave, teto in (("custo_hora", 1000000000), ("custo_adicional", 1000000000000)):
            valor = item[chave]
            if isinstance(valor, bool) or not isinstance(valor, (int, float, Decimal)):
                raise ValueError("Custos devem ser números não negativos.")
            numero(float(valor), chave, 0, teto)
        vistos.add(identificador)
        custos += Decimal(str(item["custo_hora"]))
        adicionais += Decimal(str(item["custo_adicional"]))
    if custos > 1000000000 or adicionais > 1000000000000:
        raise ValueError("A soma dos custos supera o limite permitido para a simulação.")
    combinado = copy(cenario)
    combinado.custo_hora, combinado.custo_adicional = custos, adicionais
    with vaga_simulacao():
        resultado = simular_interrupcao(combinado, n=n, seed=seed, limite=limite)
    resultado.update(versao_modelo="sauron.interrupcao-compartilhada/30d-v1", escopo=grafo["escopo"],
                     snapshot_sha256=grafo["snapshot_sha256"], relacoes_excluidas=grafo["excluidas"],
                     custos_servicos=impactos, custo_total_hora=float(custos), custo_total_adicional=float(adicionais))
    return resultado
