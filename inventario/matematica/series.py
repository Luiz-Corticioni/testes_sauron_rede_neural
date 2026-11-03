"""Euler aplicado a snapshots: dias no eixo do tempo e risco-dia na área."""

import numpy as np



class SerieRisco:
    def __init__(self, dias, totais):
        self.dias = np.asarray(dias, dtype=float)
        self.totais = np.asarray(totais, dtype=float)
        if self.dias.ndim != 1 or self.totais.shape != self.dias.shape:
            raise ValueError("Datas e totais precisam ser listas de mesmo tamanho.")
        if not np.all(np.isfinite(self.dias)) or not np.all(np.isfinite(self.totais)):
            raise ValueError("A série exige números finitos.")
        if np.any(np.diff(self.dias) <= 0) or np.any(self.totais < 0):
            raise ValueError("Datas precisam crescer; riscos não podem ser negativos.")

    def analisar(self, inicio=None, fim=None, limiar=10, janela_minima_dias=1):
        if not np.isfinite(janela_minima_dias) or janela_minima_dias<=0:
            raise ValueError("Janela de regressão deve ser positiva.")
        if len(self.dias) < 3:
            return {
                "disponivel": False,
                "alertas": [],
                "mensagem": "São necessários ao menos 3 snapshots em instantes distintos.",
            }
        a = self.dias[0] if inicio is None else float(inicio)
        b = self.dias[-1] if fim is None else float(fim)
        if not np.all(np.isfinite([a, b, limiar])) or limiar < 0:
            raise ValueError("Período e limiar precisam ser finitos; limiar não negativo.")
        if not self.dias[0] <= a < b <= self.dias[-1]:
            raise ValueError("Escolha um período crescente dentro dos snapshots disponíveis.")
        pontos = np.concatenate(([a], self.dias[(self.dias>a)&(self.dias<b)], [b]))
        if len(pontos)>50001:
            raise ValueError("O período excede 50000 segmentos.")
        indices=np.searchsorted(self.dias,pontos[:-1],side="right")-1
        area=float(np.sum(np.diff(pontos)*self.totais[indices]))
        inicio_janela=max(a,b-janela_minima_dias)
        primeiro=max(0,int(np.searchsorted(self.dias,inicio_janela,side="right"))-1)
        mascara=(self.dias>=self.dias[primeiro])&(self.dias<=b)
        x,y=self.dias[mascara],self.totais[mascara]
        taxa=None
        if len(x)>=3 and x[-1]-x[0]>=janela_minima_dias-1e-9:
            centrado=x-x.mean()
            taxa=float(centrado@(y-y.mean())/(centrado@centrado))
        alertas = []
        if taxa is not None and taxa > limiar:
            mensagem = f"Risco cresce {taxa:.4f} pontos por dia por regressão na janela de observação."
            alertas.append({"tipo": "TENDENCIA", "mensagem": mensagem})
        return {
            "disponivel": True,
            "risco_dia": round(area, 6),
            "taxa_por_dia": round(taxa, 6) if taxa is not None else None,
            "inicio_dias": float(a),
            "fim_dias": float(b),
            "ponto_derivada_dias": None,
            "limiar": limiar,
            "alertas": alertas,
            "metodo": "Degrau constante à esquerda; regressão linear em janela mínima.",
            "janela_minima_dias": janela_minima_dias,
        }
