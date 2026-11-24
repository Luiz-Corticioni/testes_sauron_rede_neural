# Qualidade e medição de escala — 24/11/2026

As telas de risco apresentam agora os componentes de EPSS e fontes para o
recorte de ativos aplicável. A API legada de risco, a simulação de correção e o
diagnóstico linear também expõem esses componentes. A revisão de cobertura sem
perímetro/camada continua indeterminada, e o índice composto não é inventado.
EPSS não foi acrescentado à fórmula de risco. Testes focados validaram recorte,
permissões e regressão dos números anteriores.

O benchmark `scripts/benchmark_api_risco_e2e.py` usa banco SQLite temporário,
cliente Django, cache limpo, uma vulnerabilidade, uma incidência e cadeia de
dependências fictícias. Em contêiner sem rede limitado a 2 CPUs e 2 GiB, uma
execução em 10 mil ativos concluiu a requisição em 0,882 s e atingiu pico de
206,84 MiB; em 100 mil, 5,001 s e 262,36 MiB. A preparação levou respectivamente
4,048 s e 17,285 s; em ambos, a API retornou HTTP 200 e 25 resultados.

Esses números não incluem login, rede TCP, TLS ou concorrência; o pico de memória
inclui a criação dos dados. A topologia é esparsa e não representa todos os
ambientes. A primeira tentativa com 10 mil ativos foi rejeitada por configuração
de `ALLOWED_HOSTS`; a medição acima é da repetição com `testserver` isolado.
O benchmark não fornece uma medição anterior do fluxo inteiro; o relatório da
fase 0 mantém a comparação anterior apenas da seleção de páginas.
