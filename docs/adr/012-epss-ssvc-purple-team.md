# 012 — EPSS/SSVC e purple team contínuo
Status: proposta; nenhuma integração externa nova nesta rodada.

Preservar valor/data/fonte do EPSS e prazo do horizonte; não interpretar EPSS como
chance de comprometimento do próprio ativo. Usar SSVC como árvore de decisão
explicável com exploração, exposição, impacto e criticidade de missão, mantendo
evidências e a versão da política. Score ausente é desconhecido, não zero.
SIS/SIR usa uma conversão de hazard apenas como hipótese de cenário, sem calibração.

Atomic Red Team/Caldera seriam usados exclusivamente em ambiente autorizado e
isolado, com inventário de testes, janela, critérios de parada, snapshots e limpeza
verificada. Nenhum teste ofensivo é disparado por esta implementação.
Purple team deve ligar hipótese→telemetria esperada→regra→resultado rotulado,
medindo cobertura por técnica ATT&CK, tempo de detecção e falsos positivos.
Avaliar por walk-forward, com embargo e labels atrasados quando necessário.
Brier, calibração e PR-AUC devem ser acompanhados da prevalência e da definição
exata da curva; fixtures sintéticas não demonstram qualidade em produção.

