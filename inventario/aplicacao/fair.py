"""Criação auditada e simulação protegida de cenários FAIR."""
from copy import deepcopy
import sys

import numpy
from django.db import transaction
from inventario.aplicacao.autorizacao import exigir
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.infraestrutura.limite_simulacoes import vaga_simulacao
from inventario.matematica.fair import simular
from inventario.models import CenarioFAIR, ExecucaoFAIR

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


def snapshot(cenario):
    campos = ('nome', 'ativo_id', 'evento', 'ameaca', 'efeito', 'escopo', 'origem_frequencia',
              'origem_suscetibilidade', 'origem_perdas', 'qualidade', 'versao_modelo')
    dados = {campo: getattr(cenario, campo) for campo in campos}
    dados['data_referencia'] = cenario.data_referencia.isoformat()
    dados['premissas'] = deepcopy(cenario.premissas)
    return dados


def executar(cenario, usuario, n=10000, seed=42, guardar=False):
    if type(guardar) is not bool:
        raise ValueError('Escolha se a execução deve ser guardada.')
    if guardar:
        exigir(usuario, *ESCRITA)
    resultado = calcular(cenario, usuario, n=n, seed=seed)
    if not guardar:
        return resultado, None
    dados = snapshot(cenario)
    with transaction.atomic():
        travar_escrita()
        usuario = exigir(usuario, *ESCRITA)
        atual = CenarioFAIR.objects.select_for_update().get(pk=cenario.pk)
        if snapshot(atual) != dados:
            raise ValueError('O cenário mudou durante a simulação; execute novamente.')
        with usar_usuario(usuario):
            execucao = ExecucaoFAIR.objects.create(cenario=atual, versao_modelo=cenario.versao_modelo,
                n=n, seed=seed, premissas_snapshot=dados, resultado=resultado,
                versao_python='.'.join(str(v) for v in sys.version_info[:3]), versao_numpy=numpy.__version__, criado_por=usuario)
            registrar_evento('SIMULAR', 'CenarioFAIR', atual.pk, {'execucao': execucao.pk, 'modelo': execucao.versao_modelo})
    return resultado, execucao


def comparar(atual, alternativa, usuario, n=10000, seed=42):
    exigir(usuario, *LEITURA)
    campos = ('ativo_id', 'evento', 'ameaca', 'efeito', 'escopo', 'versao_modelo')
    if atual.pk == alternativa.pk or any(getattr(atual, campo) != getattr(alternativa, campo) for campo in campos):
        raise ValueError('Compare análises distintas do mesmo ativo, evento, ameaça, efeito, escopo e versão.')
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError('Semente inválida.')
    base = calcular(atual, usuario, n=n, seed=seed)
    outra_semente = seed ^ 0x9E3779B9
    novo = calcular(alternativa, usuario, n=n, seed=outra_semente)
    return {'atual': base, 'alternativa': novo, 'diferenca_media': base['perda']['media'] - novo['perda']['media'],
            'semente_atual': seed, 'semente_alternativa': outra_semente, 'n': n}
