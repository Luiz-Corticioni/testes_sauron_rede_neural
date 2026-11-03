# 003 — Matching por evidência de produto e versão

Faixas NVD preservam limites inclusivos/exclusivos e o marcador vulnerable.
Comparador de tokens numéricos/alfanuméricos é determinístico, sem pretensão de cobrir
todas as semânticas dos gerenciadores de pacotes. CPE desconhecido/versão desconhecida
produz indeterminação. AND/negação NVD exige contexto adicional e permanece hipótese;
não é transformado em prova a partir de um único componente.
VEX not_affected exige CPE e justificativa; aplica apenas ao produto/versão declarados.
Não há supressão VEX sem produto. Dados existentes conservam faixas vazias até
ressincronização explícita; não há informação histórica suficiente para inventá-las.
Precisão/recall são medidos em fixture pequena e sintética; não são validação em campo.

