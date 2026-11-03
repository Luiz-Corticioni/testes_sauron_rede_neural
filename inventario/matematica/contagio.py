"""SIS/SIR em grafo, laboratório de cenários em dias; não é previsão calibrada.

EPSS de 30 dias vira hazard constante -log(1-EPSS)/30 multiplicado pela exposição.
Gamma=1/MTTR (dias). Essa associação é hipótese explícita e requer calibração:
EPSS não mede diretamente infecção, propagação lateral ou probabilidade por ativo.
"""
from datetime import datetime
import numpy as np
from scipy import sparse
from inventario.matematica.euler import metodo_euler, rk4


def campo(registro,nome):
    return registro[nome] if isinstance(registro,dict) else getattr(registro,nome)


def mttr_historico(historico):
    """Média de ABERTA/TRATAMENTO→CORRIGIDA de registros tipo HistoricoIncidencia."""
    def instante(h):
        valor=campo(h,"em")
        return datetime.fromisoformat(valor) if isinstance(valor,str) else valor
    aberturas={}
    duracoes=[]
    for h in sorted(historico,key=instante):
        codigo,status=campo(h,"incidencia_codigo"),campo(h,"para")
        if status in ("ABERTA","TRATAMENTO","ACEITA"):
            aberturas.setdefault(codigo,instante(h))
        elif status=="CORRIGIDA":
            inicio=aberturas.pop(codigo,None)
            if inicio:
                dias=(instante(h)-inicio).total_seconds()/86400
                if dias>0:
                    duracoes.append(dias)
        elif status=="MITIGADA":
            aberturas.pop(codigo,None)
    return float(np.mean(duracoes)) if duracoes else None


def taxa_beta(exposicao,epss):
    exposicao,epss=np.asarray(exposicao,dtype=float),np.asarray(epss,dtype=float)
    if (not np.all(np.isfinite(exposicao)) or np.any(exposicao<0)
            or not np.all(np.isfinite(epss)) or np.any((epss<0)|(epss>1))):
        raise ValueError("Exposição/EPSS inválidos.")
    return exposicao*(-np.log1p(-np.minimum(epss,1-1e-12)))/30


def simular(a,infectados_iniciais,exposicao,epss,mttr_dias=None,historico=(),
            dias=30,passos=300,modelo="SIS",metodo="rk4",vulnerabilidades=None,
            corrigir_vulnerabilidades=()):
    """Retorna fração I(T) esperada e redução após zerar beta dos nós corrigidos.

    Aij transmite de j para i. Estados [S,I,R] conservam soma 1 em cada nó.
    Euler/RK4 recusam saídas fora de [0,1]; reduzir o passo é responsabilidade do
    chamador. Correção reduz suscetibilidade, não cura instantaneamente I inicial.
    """
    a=sparse.csr_matrix(a,dtype=float)
    n=a.shape[0]
    inicial=np.asarray(infectados_iniciais,dtype=float)
    if (not n or a.shape!=(n,n) or inicial.shape!=(n,) or not np.all(np.isfinite(inicial))
            or np.any((inicial<0)|(inicial>1)) or not np.all(np.isfinite(a.data))
            or np.any((a.data<0)|(a.data>1))):
        raise ValueError("Grafo ou frações iniciais inválidos.")
    mttr=mttr_historico(historico) if mttr_dias is None else mttr_dias
    if mttr is None or not np.isfinite(mttr) or mttr<=0:
        raise ValueError("Informe MTTR positivo ou histórico com correção concluída.")
    if modelo not in ("SIS","SIR") or metodo not in ("euler","rk4") or not np.isfinite(dias) or dias<=0:
        raise ValueError("Modelo, método ou horizonte inválido.")
    beta=np.broadcast_to(taxa_beta(exposicao,epss),(n,)).copy()
    gamma=1/mttr
    y0=np.column_stack((1-inicial,inicial,np.zeros(n)))
    integrar=metodo_euler if metodo=="euler" else rk4
    def executar(taxas):
        def derivada(t,y):
            s,i,_=y.T
            novas=taxas*s*(a@i)
            recuperadas=gamma*i
            if modelo=="SIS":
                return np.column_stack((-novas+recuperadas,novas-recuperadas,np.zeros(n)))
            return np.column_stack((-novas,novas-recuperadas,recuperadas))
        r=integrar(derivada,y0,0,dias,passos)
        estados=np.asarray(r["estados"])
        if np.min(estados)<-1e-10 or np.max(estados)>1+1e-10:
            raise ValueError("Passo excessivo; reduza-o para conservar probabilidades.")
        r["fracao_esperada"]=float(estados[-1,:,1].mean())
        return r
    antes=executar(beta)
    mapeamento=vulnerabilidades or {}
    corrigida=beta.copy()
    for vid in corrigir_vulnerabilidades:
        if vid not in mapeamento:
            raise ValueError("Vulnerabilidade sem mapeamento de nós.")
        for indice in mapeamento[vid]:
            if type(indice) is not int or not 0<=indice<n:
                raise ValueError("Índice de nó inválido.")
            corrigida[indice]=0
    depois=executar(corrigida)
    return {"antes":antes,"depois":depois,"mttr_dias":mttr,
            "efeito_correcao":antes["fracao_esperada"]-depois["fracao_esperada"]}

