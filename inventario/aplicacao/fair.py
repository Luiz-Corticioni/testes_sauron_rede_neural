"""Criação auditada e simulação protegida de cenários FAIR."""
from django.db import transaction
from inventario.aplicacao.autorizacao import exigir
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.infraestrutura.limite_simulacoes import vaga_simulacao
from inventario.matematica.fair import simular

LEITURA = ('inventario.view_ativo', 'inventario.view_cenariofinanceiro')
ESCRITA = (*LEITURA, 'inventario.add_cenariofinanceiro')


@transaction.atomic
def criar(cenario, usuario, sem_sobreposicao):
    usuario = exigir(usuario, *ESCRITA)
    if sem_sobreposicao is not True:
        raise ValueError('Confirme que as parcelas de perda são distintas e cabem nos 30 dias.')
    travar_escrita()
    cenario.criado_por = usuario
    cenario.full_clean()
    with usar_usuario(usuario):
        cenario.save()
        registrar_evento('CRIAR', 'CenarioFAIR', cenario.pk,
                         {'ativo': cenario.ativo_id, 'modelo': cenario.versao_modelo, 'custos_distintos_declarados': True})
    return cenario


def calcular(cenario, usuario, n=10000, seed=42):
    exigir(usuario, *LEITURA)
    cenario.full_clean()
    if cenario.versao_modelo != 'sauron.fair/30d-v1':
        raise ValueError('Versão do modelo não suportada; preserve o cenário e procure atualização compatível.')
    with vaga_simulacao():
        return simular(cenario.premissas, n=n, seed=seed)
