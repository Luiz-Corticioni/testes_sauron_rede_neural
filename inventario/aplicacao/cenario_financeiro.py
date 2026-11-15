"""Cadastro e simulação de cenário de perda com autorização explícita."""
from django.db import transaction

from inventario.aplicacao.autorizacao import exigir
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.infraestrutura.limite_simulacoes import vaga_simulacao
from inventario.matematica.cenario_financeiro import simular_interrupcao


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
