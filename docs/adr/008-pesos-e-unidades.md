# 008 — Semântica de pesos e fatores

Leontief: Aij é fração adimensional de influência do risco do fornecedor j no
dependente i por salto, não probabilidade de exploração. M é incidência binária,
b é soma de CVSS base em pontos; x é pontos amplificados, sem unidade monetária e
sem interpretação como percentual de comprometimento. Índice saturado não é previsão.
Fatores de exposição multiplicam b só no perfil operacional e são heurísticas
configuráveis: SAURON_RISCO_FATORES_EXPOSICAO (JSON por tipo), multiplicadores de
internet/admin remota. Defaults preservam as constantes antigas e precisam calibração.

Política leontief exige estabilidade e mantém limite conservador de soma no cadastro.
SAURON_RISCO_POLITICA=noisy-or é SOMENTE laboratório: permite soma de linha >=1,
preservando pesos individuais e sem autodependência. Serviços de risco de produção
recusam essa política até integração aprovada. O módulo puro de F2/3 recebe
probabilidades e pesos em [0,1], sem interpretar esses dados como pontos CVSS.
Não se ativam novos modelos na aplicação nesta rodada.
