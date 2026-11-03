"""Métricas de previsão binária e avaliação temporal, sem modelo ou ORM.

PR-AUC usa trapézios na curva precision-recall com limiares agrupados por empate;
não é Average Precision. Sempre compare com prevalência e a mesma definição.
Walk-forward expande treino, não embaralha tempos e não entrega y futuro ao callback.
Features devem ter sido observáveis no instante ts; este módulo não pode provar isso.
"""
import numpy as np


def validar(y,p):
    y,p=np.asarray(y,dtype=float),np.asarray(p,dtype=float)
    if y.ndim!=1 or p.shape!=y.shape or not y.size or not np.all(np.isfinite(y)) or not np.all(np.isfinite(p)):
        raise ValueError("Vetores não vazios, finitos e de mesmo tamanho são obrigatórios.")
    if not np.all((y==0)|(y==1)) or np.any((p<0)|(p>1)):
        raise ValueError("Rótulos binários e probabilidades em [0,1] são obrigatórios.")
    return y,p


def brier(y,p):
    """Erro quadrático médio de probabilidades; menor é melhor."""
    y,p=validar(y,p)
    return float(np.mean((p-y)**2))


def calibracao(y,p,bins=10):
    """Bins uniformes, incluindo p=1 no último; ECE ponderada por contagem."""
    y,p=validar(y,p)
    if type(bins) is not int or not 1<=bins<=1000:
        raise ValueError("Número de bins inválido.")
    indices=np.minimum((p*bins).astype(int),bins-1)
    resultado=[]
    ece=0.0
    for indice in range(bins):
        selecionados=indices==indice
        n=int(selecionados.sum())
        if n:
            previsto,observado=float(p[selecionados].mean()),float(y[selecionados].mean())
            resultado.append({"inicio":indice/bins,"fim":(indice+1)/bins,"n":n,
                              "previsto":previsto,"observado":observado})
            ece+=n/len(y)*abs(previsto-observado)
    return {"bins":resultado,"ece":ece}


def pr_auc(y,p):
    """Área trapezoidal precision-recall; sem positivos retorna 0 por convenção."""
    y,p=validar(y,p)
    positivos=y.sum()
    if positivos==0:
        return 0.0
    ordem=np.argsort(-p,kind="stable")
    y,p=y[ordem],p[ordem]
    tp=np.cumsum(y)
    fins=np.r_[np.flatnonzero(p[:-1]!=p[1:]),len(p)-1]
    precisao=np.r_[1,tp[fins]/(fins+1)]
    recall=np.r_[0,tp[fins]/positivos]
    return float(np.trapezoid(precisao,recall))


def walk_forward(dados,prever,treino_minimo=30,horizonte=7,embargo=0):
    """prever(treino_com_y, teste_sem_y)→probabilidades; janela de treino expansiva."""
    if any(type(x) is not int for x in (treino_minimo,horizonte,embargo)) or treino_minimo<1 or horizonte<1 or embargo<0:
        raise ValueError("Janelas devem ser inteiras positivas e embargo não negativo.")
    if len(dados)<=treino_minimo+embargo:
        raise ValueError("Dados insuficientes.")
    if any(dados[i]["ts"]>=dados[i+1]["ts"] for i in range(len(dados)-1)):
        raise ValueError("Instantes devem crescer estritamente; não embaralhe os dados.")
    folds=[]
    observados=[]
    probabilidades=[]
    for fim_treino in range(treino_minimo,len(dados)-embargo,horizonte):
        inicio=fim_treino+embargo
        teste=dados[inicio:inicio+horizonte]
        treino=[dict(r) for r in dados[:fim_treino]]
        features=[{k:v for k,v in r.items() if k!="y"} for r in teste]
        y=[r["y"] for r in teste]
        p=list(prever(treino,features))
        validar(y,p)
        folds.append({"fim_treino":dados[fim_treino-1]["ts"],"inicio_teste":teste[0]["ts"],
                      "n_teste":len(teste),"brier":brier(y,p),"pr_auc":pr_auc(y,p)})
        observados.extend(y)
        probabilidades.extend(p)
    return {"folds":folds,"brier":brier(observados,probabilidades),
            "pr_auc":pr_auc(observados,probabilidades),
            "calibracao":calibracao(observados,probabilidades),
            "observados":observados,"probabilidades":probabilidades}

