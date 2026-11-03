# Comparação CVSS e conferência matemática — 27/10/2026

## Usar o comparador

No menu web, abra **Comparar CVSS**. Também há um link nas vulnerabilidades,
na ficha do ativo e nos resultados da consulta CVE/KEV.

1. Informe a CVE. O vetor 3.1 pode vir do cadastro selecionado, ser informado pelo
   usuário ou, quando o campo está vazio, ser extraído da avaliação 3.1 da NVD.
2. Marque **Atualizar pela internet** para uma consulta explícita. Desmarcado, o
   sistema usa somente cache local. Abrir a página por GET não faz download.
3. Leia as notas, vetores, publicadores e data. A diferença principal é
   **4.0 publicado − 3.1 calculado localmente**, em pontos.
4. Confira também **3.1 NVD − 3.1 local**. Para o mesmo vetor base, divergência
   merece revisão. Vetores diferentes podem representar avaliações diferentes.

No terminal: menu **CVE, KEV E CVSS → opção 7**. O cálculo e a seleção das
avaliações usam o mesmo serviço da web. O terminal pede confirmação antes de
atualizar pela internet.

A comparação não grava notas ou estados das incidências. Se selecionar um cadastro
com nota diferente do vetor calculado, a tela alerta e oferece revisão do cadastro.
Não se decide automaticamente se o erro está na nota ou na avaliação do vetor.

## O que é conferido

O cálculo local cobre CVSS **Base 3.1** conforme FIRST. Vetores ambientais/temporais
válidos da fonte são validados, mas somente suas oito métricas base entram nessa
comparação. Um vetor manual do comparador deve conter somente as métricas base.

A nota **4.0 é recebida da NVD**, mantendo `source`, `type`, vetor e a data do cache.
São validados versão, estrutura, métricas obrigatórias/opcionais, duplicatas,
valores finitos, faixa e precisão de uma casa decimal. Não foi implementado um
calculador local 4.0: a estrutura válida não atesta que o publicador calculou a nota
corretamente. A tela explicita essa distinção.

Se o vetor 4.0 contém ameaça ou ambiente definidos (CVSS-BT/BE/BTE), ele é identificado
e não se calcula diferença contra a base 3.1. Métricas suplementares não alteram essa
classificação. Notas indisponíveis não viram zero; uma nota explicitamente zero é preservada.
CVE rejeitada não produz comparação operacional.

A seleção prioriza avaliações com vetor utilizável e o publicador `nvd@nist.gov`, depois
`Primary`. Uma nota com vetor inválido é identificada como não utilizável para comparação. As demais avaliações ficam disponíveis para inspeção. Se os publicadores
forem distintos, há aviso. Isso também corrige a antiga seleção por CPE, que podia
usar o primeiro item de uma lista mesmo quando a consulta web usava outra avaliação.

O cache mostra a data original da consulta. Se uma atualização falhar, uma cópia local
válida pode ser exibida com o erro de atualização e indicação de expiração após 24 horas.
Uma falha não é apresentada como consulta bem-sucedida à internet.

CVSS mede gravidade 0–10. O risco matricial agrega incidências e dependências,
pode ultrapassar 10 e tem índice próprio 0–100. A diferença entre versões não é erro
matemático por si só, probabilidade de ataque ou variação do índice matricial.

## Orientação para stakeholders

O **Guia rápido** explica o fluxo de uso, CVE, CVSS, vetor, NVD/CNA, KEV, EPSS,
CPE, C–I–A, incidências, aceite, sistema imune, SLA e MTTR. As telas principais têm
blocos recolhíveis de ajuda com instruções curtas e links para o guia.

Foram corrigidos textos que falavam em interpolação linear no histórico, embora a
área seja calculada por degraus à esquerda. O ranking também esclarece que contexto
ambiental precede ganho na ordenação, quando esse contexto está disponível.
Os ajustes de exposição/KEV pertencem à política do modelo interno, sem mudar o CVSS.

## Auditoria dos cadastros

```bash
python manage.py auditar_cvss
python manage.py auditar_cvss --json
```

O comando é de leitura: conta notas, recalcula as bases 3.1 com vetor e lista
divergências. Notas sem vetor e versões sem recálculo são contabilizadas separadamente.
Divergências produzem código de saída não zero; não há correção automática do banco.
As gravações também rejeitam NaN, infinitos, notas fora de 0–10 ou sem precisão CVSS
válida, antes de chegar ao banco.

## Evidências da revisão

- CVSS Base 3.1: **2.592 vetores** comparados com referência literal independente
  da FIRST, além de notas públicas conhecidas e fronteiras de arredondamento.
- Ambiental/temporal: **2.000 vetores** determinísticos com métricas modificadas,
  requisitos e fatores temporais, comparados com referência Decimal de 45 dígitos;
  preservados os 128 cenários de C–I–A da suíte anterior.
- Risco: **50 grafos × 2 perfis** comparados com solução densa independente,
  conferindo resíduos, índices e simulações de correção.
- Derivadas, Simpson, trapézios, Euler e RK4 comparados com soluções analíticas e
  refinamento de passo; risco-dia conferido também em intervalo parcial.
- Matriz esparsa de 5.000 ativos preservada. Corrigido o raio espectral de grafos
  acíclicos grandes: o método anterior podia informar 0,2 em vez de zero. Agora
  verifica componentes fortemente conexas; grafos cíclicos usam análise espectral.
- Derivadas recusam passos que não distinguem `x±h` de `x`, além de denominadores
  nulos/não finitos. Isso evita falso resultado zero e erro de divisão não tratado.
- Corrigida a normalização de espaços em vetores ambientais.
- Rede, permissões, CSRF, cache expirado, múltiplos publicadores, versões ausentes,
  notas zero, métricas inválidas e dados divergentes exercitados com mocks/fixtures.

A fixture pública `tests/fixtures/nvd_cvss_duas_versoes.json` foi extraída da API
oficial em 27/10/2026. Para CVE-2024-7450, a NVD informou 3.1 **8,8** e 4.0 **8,7**
na avaliação `nvd@nist.gov`; o recálculo local confirmou 8,8 e a diferença foi −0,1.
Essa consulta foi exercitada no navegador com uma cópia descartável. Também foi
conferido CVE-2024-3094: 3.1 10,0 e ausência de 4.0 na resposta daquela consulta.
Isso é um retrato datado, não uma expectativa fixa sobre respostas futuras.

A conferência dos dados de uso foi feita em SQLite com `mode=ro`/`query_only`;
o relatório específico fica fora do pacote de código. Nenhuma migração de esquema
ou alteração automática dos dados de uso foi necessária.

Testes não comprovam ausência de falhas para toda entrada ou calibração do modelo
em produção. O 4.0 externo não é recalculado localmente. Notas sem vetor e avaliações
legadas divergentes precisam de revisão do responsável pelo inventário.

## Resultado da execução

**151 testes aprovados** na suíte completa (37,8 s na execução final), mantendo
as referências golden anteriores. Ruff, Bandit, sintaxe JavaScript, `check`,
`makemigrations --check` e `check --deploy` de produção simulada aprovados.
A instalação de uma cópia nova compilou 32 templates e publicou estáticos em modo
produção. Navegação, login/MFA, comparação com API real, ausência de 4.0 e guia
foram conferidos no navegador, sem erros de console nos fluxos inspecionados.
Nenhuma dependência de execução foi acrescentada.

## Fontes oficiais

- [FIRST — especificação CVSS 3.1](https://www.first.org/cvss/v3-1/specification-document)
- [FIRST — especificação CVSS 4.0](https://www.first.org/cvss/v4.0/specification-document)
- [API NVD — amostra consultada](https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=CVE-2024-7450)
- [Registro CVE-2024-7450 na NVD](https://nvd.nist.gov/vuln/detail/CVE-2024-7450)
- [FIRST — EPSS](https://www.first.org/epss/)
- [CISA — KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog)


## Rastreabilidade

- `a27b5c2` — CV01: conferir cálculos e corrigir limites numéricos
- `65dbd3c` — CV02: comparar CVSS 3.1 e 4.0 da NVD e orientar stakeholders
