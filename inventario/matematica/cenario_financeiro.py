"""Simulação didática de interrupção em 30 dias; entradas não calibradas."""
import numpy as np

from inventario.matematica.montecarlo import numero, pert, resumo


def simular_interrupcao(cenario, n=20000, seed=42, limite=None):
    if type(n) is not int or not 100 <= n <= 100000:
        raise ValueError("Informe entre 100 e 100000 cenários.")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ValueError("Semente inválida.")
    probabilidade = numero(float(cenario.probabilidade), "Probabilidade", 0, 1)
    apos = None if cenario.probabilidade_apos is None else numero(float(cenario.probabilidade_apos), "Probabilidade após controle", 0, 1)
    minimo, moda, maximo = (float(cenario.horas_min), float(cenario.horas_moda), float(cenario.horas_max))
    custo_hora = numero(float(cenario.custo_hora), "Custo por hora", 0, 1000000000)
    adicional = numero(float(cenario.custo_adicional), "Custo adicional", 0, 1000000000000)
    if limite is not None:
        limite = numero(limite, "Limite financeiro", 0, 1e15)
    rng = np.random.default_rng(seed)
    sorteios = rng.random(n)
    duracao = pert(minimo, moda, maximo, n, rng)
    # Na ausência de informação mais específica, o início é uniforme dentro
    # da janela; contabiliza-se apenas a interrupção que ocorre até seu fim.
    inicio_horas = rng.uniform(0, 720, n)
    impacto = np.minimum(duracao, 720 - inicio_horas) * custo_hora + adicional
    evento = sorteios < probabilidade
    perda = np.where(evento, impacto, 0.0)
    resultado = {"versao_modelo": "sauron.interrupcao/30d-v2", "horizonte_dias": 30, "n": n, "seed": seed,
                 "atual": resumo(perda), "eventos": int(evento.sum()),
                 "perda_media_condicional": float(impacto[evento].mean()) if evento.any() else None,
                 "limite": limite, "excedencia": float((perda > limite).mean()) if limite is not None else None,
                 "apos": None, "diferenca_media": None}
    # Mantém ocorrência e início comuns e varia somente a duração, tratando
    # mínimo e máximo declarados como valores fixos, não como probabilidades.
    restante = 720 - inicio_horas
    perdas_minimas = np.where(evento, np.minimum(minimo, restante) * custo_hora + adicional, 0.0)
    perdas_maximas = np.where(evento, np.minimum(maximo, restante) * custo_hora + adicional, 0.0)
    resultado["sensibilidade_duracao"] = {
        "horas_min": minimo, "media_min": float(perdas_minimas.mean()),
        "media_base": resultado["atual"]["media"],
        "horas_max": maximo, "media_max": float(perdas_maximas.mean()),
    }
    if apos is not None:
        alternativa = np.where(sorteios < apos, impacto, 0.0)
        resultado["apos"] = resumo(alternativa)
        resultado["diferenca_media"] = float((perda - alternativa).mean())
    return resultado


def simular_afetacao_condicional(cenario, impactos, n=20000, seed=42, limite=None):
    """Evento comum; serviços sorteados independentemente, condicionados ao evento."""
    # Reutiliza as validações do modelo individual e conserva seus sorteios iniciais.
    base = simular_interrupcao(cenario, n=n, seed=seed, limite=limite)
    rng = np.random.default_rng(seed)
    ocorrencia = rng.random(n)
    minimo, moda, maximo = (float(cenario.horas_min), float(cenario.horas_moda), float(cenario.horas_max))
    duracao = pert(minimo, moda, maximo, n, rng)
    restante = 720 - rng.uniform(0, 720, n)
    horas = np.minimum(duracao, restante)
    custo = np.full(n, float(cenario.custo_hora))
    adicional = np.full(n, float(cenario.custo_adicional))
    contagens = []
    evento = ocorrencia < float(cenario.probabilidade)
    for item in impactos:
        afetado = rng.random(n) < float(item['probabilidade_condicional'])
        custo += afetado * float(item['custo_hora'])
        adicional += afetado * float(item['custo_adicional'])
        contagens.append(int((evento & afetado).sum()))
    impacto = horas * custo + adicional
    perda = np.where(evento, impacto, 0.0)
    base.update(versao_modelo='sauron.afetacao-condicional/30d-v1', atual=resumo(perda),
                eventos=int(evento.sum()), perda_media_condicional=float(impacto[evento].mean()) if evento.any() else None,
                excedencia=float((perda > limite).mean()) if limite is not None else None,
                afetacoes_por_servico=contagens,
                sensibilidade_duracao={'horas_min': minimo,
                    'media_min': float(np.where(evento, np.minimum(minimo, restante)*custo+adicional, 0).mean()),
                    'media_base': float(perda.mean()), 'horas_max': maximo,
                    'media_max': float(np.where(evento, np.minimum(maximo, restante)*custo+adicional, 0).mean())})
    if cenario.probabilidade_apos is not None:
        alternativa = np.where(ocorrencia < float(cenario.probabilidade_apos), impacto, 0.0)
        base['apos'] = resumo(alternativa)
        base['diferenca_media'] = float((perda-alternativa).mean())
    return base
