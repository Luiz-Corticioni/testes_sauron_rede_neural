# Fase 1 — qualidade e estado dos dados — 21/11/2026

**Estado: implementação parcial; requisitos pendentes listados abaixo.** A base inicial da branch executou 553 testes Django
com sucesso, quatro exclusivos de PostgreSQL pulados no SQLite.

## Estado das fontes

O diagnóstico já distinguia idade, cobertura e histórico de tentativas NVD/EPSS;
a etapa acrescenta histórico sanitizado de tentativas KEV e uma síntese das
fontes com origem, data e idade dos dados locais. A síntese distingue dados
atuais, vencidos, vazios, incompletos e falha na última tentativa. Uma falha
passada não demonstra que a fonte permaneça inacessível; resposta recebida não
garante dado válido, e cache atual não comprova conectividade.

Importações manuais de scanner são apresentadas apenas a quem tem as permissões
de leitura necessárias, com origem, observação, recebimento e contagem. Não há
prazo de validade ou cobertura completa inferidos dessas importações. Falhas de
gravação são registradas com categoria genérica, sem conteúdo do relatório;
sucessos só são registrados depois do commit. Prévias não entram no histórico.

`python manage.py test tests.test_estado_fontes tests.test_historico_fontes
--noinput`: 14 testes aprovados, com fontes externas simuladas. `ruff check .`
passou. Sem migração nesta etapa.

## Índice de evidências e visualização

Foi acrescentado `sauron.qualidade/1`, uma média explícita de componentes de
completude com pesos iguais, nunca interpretada como risco ou probabilidade.
Quando faltar contexto ou denominador, o índice composto é indisponível. O ativo
pode ser avaliado em um perímetro e camada; o serviço usa seu perímetro e a
camada de negócio. EPSS, revisão e estado local das fontes têm componentes e
origens explícitos. O [guia](QUALIDADE_DADOS.md) documenta os critérios e limites.

As fichas de ativo e serviço e as APIs v1 mostram esses componentes conforme
as permissões. O Monte Carlo, FAIR e cenários de interrupção informam o que foi
declarado e o que não possui validação independente; nesses casos o índice
financeiro permanece indisponível. Registros FAIR antigos não são reavaliados
retroativamente. O painel e as telas de risco informam que não há índice
agregado calculado para o recorte, em vez de exibir um valor arbitrário.

Na revisão dos serviços relacionados, importação e revisão de scanner e criação
FAIR passaram a revalidar autorização após a trava de escrita. Testes simulam
desativação da conta após a trava. A tela de prioridades também deixou de exibir
um índice zero quando o cálculo estiver indisponível.

Uma CVE vazia não é considerada evidência EPSS válida, mesmo quando um registro
inconsistente repete esse valor vazio. O resultado de causa compartilhada também
mostra os componentes de qualidade das premissas.

## Verificações realizadas

- Antes dos últimos ajustes pontuais de CVE vazia e apresentação da causa
  compartilhada, a suíte completa passou com 568 testes no Windows e em Linux
  no Docker; quatro testes exclusivos de PostgreSQL foram pulados em cada execução.
- Os testes focados de qualidade, scanner e FAIR passaram em PostgreSQL local
  descartável, antes das últimas alterações. A execução completa em PostgreSQL
  não foi realizada.
- Após os últimos ajustes, 62 testes focados de qualidade, Monte Carlo e
  cenários financeiros passaram novamente em container sem rede.
- A auditoria `pip-audit` das dependências não encontrou vulnerabilidades
  conhecidas; o Trivy não reportou CVEs nos pacotes de sistema e Python da imagem
  construída para esta verificação. Isso depende da base de dados e da imagem
  analisadas e não comprova ausência de vulnerabilidades desconhecidas.
- Ruff, Bandit, mypy no escopo configurado, validação OpenAPI e os scripts de
  interface passaram antes dos últimos ajustes pontuais. A CI do GitHub não foi
  executada para esta branch local.

## Pendente

Completar a avaliação de qualidade em todas as telas e resultados de risco,
principalmente os módulos de laboratório e fluxos que não possuem perímetro
declarado; avaliar formas de registrar validação independente das premissas sem
inventá-la; concluir testes integrais em PostgreSQL e verificações de CI da fase.
A medição ponta a ponta de escala e demais pendências da Fase 0 permanecem no
relatório anterior.
