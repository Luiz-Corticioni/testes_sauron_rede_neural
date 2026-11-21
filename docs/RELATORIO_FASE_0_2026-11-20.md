# Fase 0 — registro parcial de execução — 20/11/2026

**Situação: fase não concluída.** Este registro distingue resultados locais de
itens ainda pendentes; não é uma certificação da aplicação.

**Atualização de 21/11/2026:** a licença Apache 2.0 foi escolhida pelo responsável;
veja [a decisão](DECISAO_LICENCA.md).

## Demonstração operacional

No estado inicial da branch foram executados `python manage.py test
tests.test_demo_operacional --noinput`: sete testes passaram usando Django
5.2.19. Incluem dupla aprovação, repetição sem duplicação, preservação de base
existente e rollback da cadeia em uma falha simulada. A falha histórica de autoria
não foi reproduzida neste ensaio; portanto não se alterou a invariante nem se
declarou uma correção nova. A primeira tentativa falhou em dois testes porque o
ambiente Python localizado não tinha Argon2; a repetição usou os pacotes locais
do projeto e passou.

## Ordenação por risco da API

A versão anterior carregava todos os campos de todos os resultados antes de
ordenar. A nova implementação percorre identificadores, seleciona os necessários
e busca os campos da página. Se um identificador não aparece no cálculo, retorna
503 em vez de atribuir zero. Desempate por identificador e permissões existentes
foram preservados. Testes: `python manage.py test tests.test_api_v1_sprint5
--noinput`, nove aprovados, incluindo páginas intermediárias, empates e filtro.

`python scripts/benchmark_paginacao_risco.py` cria tabela SQLite sintética
temporária e compara as implementações na primeira e última páginas, com riscos
pré-calculados; mede tempo de seleção e pico de alocações Python via tracemalloc.
Em Windows, Python 3.12.14, Django 5.2.19, uma execução apresentou:

| Ativos sintéticos | Página | Anterior | Nova seleção |
|---:|---|---:|---:|
| 10.000 | Primeira | 0,055 s; 5,58 MiB | 0,010 s; 0,61 MiB |
| 10.000 | Última | 0,054 s; 5,51 MiB | 0,010 s; 0,52 MiB |
| 100.000 | Primeira | 0,868 s; 54,83 MiB | 0,119 s; 5,50 MiB |
| 100.000 | Última | 0,712 s; 54,77 MiB | 0,088 s; 5,50 MiB |

O script confere que os resultados da página coincidem. **Limitações:** não mede
memória nativa/RSS, tempo de autenticação, concorrência, cache, PostgreSQL ou
o cálculo real de risco. Este continua global e dependente do número de ativos,
vulnerabilidades e relações; a seleção de páginas próximas ao meio ainda pode
reter quantidade de identificadores proporcional ao total. Os números não demonstram capacidade de produção
com 100 mil ativos. Ainda é necessário um benchmark ponta a ponta com o modelo
real, perfis representativos e memória do processo.

Como medição adicional, `python scripts/benchmark_modelo_risco.py 10000` e
`python scripts/benchmark_modelo_risco.py 100000` executaram o modelo matemático
real em processos separados: uma vulnerabilidade, uma incidência e uma cadeia
de dependências com peso 0,2. Para 10 mil ativos, cálculo e serialização levaram
0,032 s, com pico de memória residente do processo de 68,03 MiB; para 100 mil,
0,358 s e 145,66 MiB. Os picos incluem imports e preparação do processo. Não
são medições antes/depois nem incluem banco, autorização, cache ou HTTP; uma
única vulnerabilidade e uma cadeia esparsa não representam todos os inventários.

## Imagem e PostgreSQL

Os 47 achados históricos pertencem à imagem Debian anterior; o
[relatório Alpine](RELATORIO_IMAGEM_ALPINE_2026-11-15.md) registra ausência de
HIGH/CRITICAL na varredura daquele artefato e daquela data. Isso não caracteriza
a imagem atual. Após iniciar o Docker Desktop fora do isolamento da sessão,
uma imagem local foi construída e analisada pelo Trivy 0.76.2 a partir de um
arquivo exportado, sem montar o socket Docker; a execução terminou com código 0
para HIGH/CRITICAL. Uma reconstrução sem cache atualizou `libcrypto3`, `libssl3`,
`krb5-libs` e `zlib`; em seguida a imagem com a correção do backup foi construída
usando essas camadas. A varredura de arquivo exportado com Trivy 0.76.2 terminou
com código 0 e registrou **zero achados HIGH/CRITICAL** em dois alvos detectados.
O resultado é limitado à imagem e à base de vulnerabilidades naquela execução;
não demonstra ausência de falhas. Não foram desativados alertas nem alterada a
política do workflow.

Uma segunda imagem, contendo as credenciais e migrações novas, também foi
exportada e analisada com Trivy 0.76.2: código 0, dois alvos e zero achados
HIGH/CRITICAL. A análise usou arquivo montado somente para leitura, sem acesso
ao socket Docker.

Em PostgreSQL 16 temporário, isolado e acessível somente por loopback, todas as
migrações passaram usando psycopg 3.2.12 instalado em pasta de testes, sem
alteração das dependências do projeto. O teste `tests.test_postgres_concorrencia`
verificou oito gravações simultâneas e cadeia íntegra. Um backup lógico do
PostgreSQL, com quatro ativos fictícios, foi restaurado para SQLite novo e a
contagem conferiu; isso não prova restauração para PostgreSQL, que o projeto
atualmente não implementa. TLS foi desativado exclusivamente na conexão local
descartável; não é configuração recomendada para produção.

Uma execução de 83 testes de API, relações e cobertura em PostgreSQL terminou
com dois erros: testes de backup são executados dentro de `TestCase`, que já
abriu uma transação, e o backup precisa iniciar `REPEATABLE READ` antes de
consultas. Fora dessa transação, o backup descrito acima funcionou. O código agora
recusa uma chamada aninhada com mensagem explícita, sem enfraquecer o isolamento.
Três testes PostgreSQL passaram: recusa sem invalidar a transação, oito gravações
simultâneas e backup/restauração em `TransactionTestCase`, incluindo autoria e
evidência de relação, membros de perímetro e revisão. A repetição da suíte de
API, relações, cobertura e PostgreSQL terminou com 86 testes, dois pulados:
os dois testes originais envoltos em `TestCase` são substituídos no PostgreSQL
pelo teste transacional equivalente. Essa seleção não é a suíte PostgreSQL inteira.

## Outras verificações e pendências

Suíte Django inicial: 538 testes passaram; após a alteração, 539 testes passaram.
Na imagem Linux, com rede desativada, 542 testes foram executados com sucesso,
dos quais dois testes exclusivos de PostgreSQL foram pulados; um terceiro teste
de PostgreSQL foi acrescentado posteriormente e validado no banco temporário.
Após a implementação das credenciais, a imagem atual executou 552 testes com
sucesso e quatro exclusões exclusivas de PostgreSQL.
No Windows, a suíte final executou 553 testes com quatro exclusões PostgreSQL,
incluindo o teste adicional de isolamento entre administradores.
`python -m pytest -q testes_pytest`:
6 passaram; `ruff check .`, mypy no escopo de dois arquivos do CI, bandit e
`makemigrations --check --dry-run` passaram. Bandit informou aviso de anotação
`nosec` existente em `backup.py`; isso não significa auditoria completa.
O validador OpenAPI e os onze scripts JavaScript do workflow passaram;
`python scripts/check_producao.py` informou nenhum problema.

O teste `scripts/testar_smtp_local.py` inicialmente falhou com `WinError 10013`
ao tentar conectar ao servidor local no ambiente restrito. Após liberar acesso
de rede para a execução, passou com STARTTLS, certificado e autenticação
simulados. Não testa entrega externa de e-mails. Uma execução de `pip-audit
--disable-pip --no-deps -r requirements.txt` fora do isolamento consultou a
base e não indicou vulnerabilidades conhecidas nas dependências diretamente
fixadas. A execução posterior `pip-audit -r requirements.txt --progress-spinner off`,
com resolução de dependências transitivas, também terminou sem vulnerabilidades
conhecidas reportadas; o resultado depende da resolução e da base naquela data.

## Credenciais de integração

A API aceita credenciais `Bearer` apenas nas duas consultas de inventário,
com escopos de leitura separados. Emissão, listagem, rotação e revogação são
restritas ao superusuário proprietário por sessão; as escritas exigem MFA,
reautenticação recente e CSRF. A credencial tem prazo de 1 a 90 dias, segredo
aleatório exibido uma vez, hash persistido e limite por credencial e origem.
A rotação é atômica e a trilha registra criação, uso, falhas e revogação sem o
segredo. Backups e exportações excluem credenciais, evitando reativá-las após
restauração. Detalhes e limitações: [guia](CREDENCIAIS_INTEGRACAO.md) e
[ADR 014](adr/014-credenciais-integracao.md).

Testes específicos cobriram credencial válida, inválida, expirada, revogada,
sem escopo, rotação, rollback, rate limit, MFA, CSRF e reautenticação. No
PostgreSQL, oito acessos concorrentes ao mesmo token respeitaram o limite de
quatro no ensaio; o teste verificou ainda a cadeia de auditoria. O conjunto de
API, credenciais, relações, cobertura e concorrência executou 95 testes no
PostgreSQL: passou com três exclusões de testes `TestCase` de backup, cobertos
por cenário equivalente em `TransactionTestCase`. A latência e capacidade de
produção do limitador não foram medidas.

A escolha da Apache 2.0 está registrada em [DECISAO_LICENCA.md](DECISAO_LICENCA.md).
Faltam as verificações finais da fase, incluindo execução integral do CI e suas
verificações na imagem atualizada.
