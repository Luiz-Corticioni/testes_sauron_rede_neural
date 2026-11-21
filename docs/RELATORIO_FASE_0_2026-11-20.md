# Fase 0 — registro parcial de execução — 20/11/2026

**Situação: fase não concluída.** Este registro distingue resultados locais de
itens ainda pendentes; não é uma certificação da aplicação.

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
--noinput`, oito aprovados.

`python scripts/benchmark_paginacao_risco.py` cria tabela SQLite sintética
temporária e compara as implementações na **primeira página**, com riscos
pré-calculados; mede tempo de seleção e pico de alocações Python via tracemalloc.
Em Windows, Python 3.12.14, Django 5.2.19, uma execução apresentou:

| Ativos sintéticos | Anterior | Nova seleção |
|---:|---:|---:|
| 10.000 | 0,053 s; 5,58 MiB | 0,010 s; 0,61 MiB |
| 100.000 | 0,669 s; 54,83 MiB | 0,088 s; 5,50 MiB |

O script confere que os resultados da página coincidem. **Limitações:** não mede
memória nativa/RSS, tempo de autenticação, concorrência, cache, PostgreSQL ou
o cálculo real de risco. Este continua global e dependente do número de ativos,
vulnerabilidades e relações; páginas profundas também podem exigir memória
proporcional ao deslocamento. Os números não demonstram capacidade de produção
com 100 mil ativos. Ainda é necessário um benchmark ponta a ponta com o modelo
real, perfis representativos e memória do processo.

## Imagem e PostgreSQL

Os 47 achados históricos pertencem à imagem Debian anterior; o
[relatório Alpine](RELATORIO_IMAGEM_ALPINE_2026-11-15.md) registra ausência de
HIGH/CRITICAL na varredura daquele artefato e daquela data. Isso não caracteriza
a imagem atual. `docker version --format '{{.Server.Version}}'` não conseguiu
conectar ao mecanismo Docker local. A tentativa de iniciar o Desktop não o tornou
disponível. Faltam reconstrução, nova triagem Trivy e validações reais de
migração, concorrência e restauração PostgreSQL; nenhum resultado foi presumido.

## Outras verificações e pendências

Suíte Django inicial: 538 testes passaram; após a alteração, 539 testes passaram.
`python -m pytest -q testes_pytest`:
6 passaram; `ruff check .`, mypy no escopo de dois arquivos do CI, bandit e
`makemigrations --check --dry-run` passaram. Bandit informou aviso de anotação
`nosec` existente em `backup.py`; isso não significa auditoria completa.
O validador OpenAPI e os onze scripts JavaScript do workflow passaram;
`python scripts/check_producao.py` informou nenhum problema.

O teste `scripts/testar_smtp_local.py` inicialmente falhou com `WinError 10013`
ao tentar conectar ao servidor local no ambiente restrito. Após liberar acesso
de rede para a execução, passou com STARTTLS, certificado e autenticação
simulados. Não testa entrega externa de e-mails. `pip-audit -r
requirements.txt` falhou ao tentar preparar ferramentas do ambiente isolado;
uma segunda tentativa com `--disable-pip --no-deps` foi interrompida após não
apresentar resultado. Nenhuma conclusão sobre vulnerabilidades atuais das
dependências é possível.

Tokens máquina-a-máquina ainda não foram implementados. A integração deve
considerar que a API atual depende do middleware de sessão e MFA, sem abrir
exceções genéricas para rotas sensíveis. A escolha de licença está pendente em
[DECISAO_LICENCA.md](DECISAO_LICENCA.md). Faltam as verificações finais da fase,
incluindo execução integral do CI e suas verificações de imagem.
