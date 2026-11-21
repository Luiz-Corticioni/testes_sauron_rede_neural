"""Extremos declarados de uma premissa FAIR; não calcula valor da informação."""
from copy import deepcopy
from inventario.aplicacao.autorizacao import exigir
from inventario.aplicacao.fair import LEITURA
from inventario.infraestrutura.limite_simulacoes import vaga_simulacao
from inventario.matematica.fair import simular

FATORES = {'frequencia', 'acao', 'suscetibilidade', 'capacidade', 'resistencia', 'slef'}


def analisar(cenario, usuario, fator, indice=None, n=1000, seed=42):
    exigir(usuario, *LEITURA)
    cenario.full_clean()
    if cenario.versao_modelo not in ('sauron.fair/30d-v1', 'sauron.fair/30d-v2'):
        raise ValueError('Versão de modelo não suportada.')
    if type(n) is not int or not 100 <= n <= 3000 or type(seed) is not int or not 0 <= seed <= 2**32-1:
        raise ValueError('Informe entre 100 e 3.000 simulações e uma semente válida.')
    dados = cenario.premissas
    if not isinstance(fator, str):
        raise ValueError('Escolha uma premissa disponível neste cenário.')
    if fator == 'valor_perda':
        if type(indice) is not int or not 0 <= indice < len(dados['perdas']):
            raise ValueError('Escolha uma parcela de perda existente.')
        faixa = dados['perdas'][indice]['valor']
    elif fator in FATORES and indice is None and dados.get(fator) is not None:
        faixa = dados[fator]
    else:
        raise ValueError('Escolha uma premissa disponível neste cenário.')
    extremos = []
    for valor in (faixa[0], faixa[2]):
        variante = deepcopy(dados)
        if fator == 'valor_perda':
            variante['perdas'][indice]['valor'] = [valor, valor, valor]
        else:
            variante[fator] = [valor, valor, valor]
        extremos.append(variante)
    with vaga_simulacao():
        medias = [simular(premissas, n=n, seed=seed)['perda']['media']
                  for premissas in (dados, *extremos)]
    from inventario.aplicacao.qualidade_dados import qualidade_premissas
    return {'faixa': faixa, 'media_base': medias[0], 'media_min': medias[1], 'media_max': medias[2],
            'n': n, 'seed': seed, 'modelo': cenario.versao_modelo,
            'qualidade_dados': qualidade_premissas(cenario)}
