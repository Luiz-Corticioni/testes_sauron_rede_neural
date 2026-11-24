# Correções de pendências — 24/11/2026

Branch `correcoes-pendencias-plano`. Registro parcial: a existência deste arquivo
não significa que todas as pendências do plano original estejam resolvidas.

## Qualidade nos recortes de risco

O serviço `qualidade_recorte_risco` apresenta dados EPSS recentes e coerentes
para as incidências abertas, em tratamento ou aceitas do mesmo recorte usado no
modelo. Quando houver filtros no painel, são considerados apenas os ativos do
filtro; o estado de fontes NVD/KEV continua sendo global e está identificado como
tal. O sistema inclui os componentes no painel, mapa, matrizes, prioridades e
nas respostas das APIs legadas de risco, simulação e diagnóstico linear.

A cobertura de relações continua indeterminada quando não há perímetro e camada
declarados para o recorte, impedindo um índice composto falso. A avaliação por
ativo ou serviço continua disponível para perímetros específicos. O EPSS é
exibido como dado de contexto de qualidade; não se atribuiu contribuição fictícia
à fórmula de risco que não o utiliza. Os modelos matemáticos e a ordenação não
foram alterados. A apuração das fontes envolve leituras locais adicionais; seu
impacto em carga simultânea ainda precisa ser medido.

Os testes focados `tests.test_qualidade_dados` e `tests.test_regressao`
passaram: conferem diferença entre recorte e total, ausência de cobertura,
permissão e manutenção do golden matemático. Uma primeira suíte completa
identificou que o teste golden comparava a resposta inteira anterior; o teste foi
ajustado para verificar a saída matemática e o novo campo separadamente.

## Benchmark com banco e rota Django

`scripts/benchmark_api_risco_e2e.py` cria banco SQLite temporário, executa
migrações e percorre `/api/v1/ativos/?ordenar=-risco` com sessão e MFA de teste.
O cálculo real de risco é executado com cache limpo. Dados são fictícios;
preparação usa inserção em lote no banco descartável, sem os serviços normais de
cadastro, exclusivamente para gerar volume. O script não altera um banco existente.

Em contêiner Linux, com limite de 2 CPUs e 2 GiB, sem rede, uma execução por
tamanho produziu:

| Ativos | Dependências | Preparação | Requisição WSGI | Pico RSS do processo | Resultado |
|---:|---:|---:|---:|---:|---|
| 10.000 | 9.999 | 4,048 s | 0,882 s | 206,84 MiB | HTTP 200; 25 resultados |
| 100.000 | 99.999 | 17,285 s | 5,001 s | 262,36 MiB | HTTP 200; 25 resultados |

Há uma vulnerabilidade, uma incidência e cadeia esparsa de dependências em cada
ensaio. O tempo da requisição inclui ORM, cálculo e serialização, mas não inclui
login, TCP, TLS, proxy, concorrência ou PostgreSQL. O pico inclui a preparação.
Não foram realizadas medições ponta a ponta **antes** da alteração histórica;
os números antes/depois existentes referem-se à seleção sintética de página, no
[relatório da fase 0](RELATORIO_FASE_0_2026-11-20.md). Não são evidência de
capacidade geral com 100 mil ativos ou vulnerabilidades. A primeira execução de
10 mil falhou por `ALLOWED_HOSTS` no ambiente do cliente de testes; após configurar
`testserver` somente no processo de benchmark, a repetição passou.

## Posicionamento e laboratórios

O README agora explicita o propósito e os limites da aplicação; Euler, sistema
imune e iscas foram identificados na navegação como laboratório. O
[roadmap](ROADMAP_ATUAL.md) relaciona estado, evidências e pendências, incluindo
contágio. O workflow já continha geração e upload de SBOM; não se alegou uma
publicação no GitHub sem verificar a execução correspondente.

## Retenção das observações

O responsável definiu **90 dias por padrão**, configuráveis entre 30 e 180 dias.
Em **Observações → Configurar retenção**, um usuário com as permissões específicas
pode alterar o prazo; a alteração é auditada após nova verificação de acesso.
É preciso aplicar as migrações `0047` a `0049` e, conforme a política do ambiente, atualizar
as permissões dos grupos. O comando `configurar_grupos` substitui as permissões
dos grupos padrão e deve ser revisado antes do uso em instalações customizadas.
Reduzir o prazo pode tornar dados elegíveis à exclusão irreversível. Para evitar
reexposição, a ampliação é recusada enquanto houver dados já vencidos aguardando
processamento pelo prazo anterior.

O prazo é contado a partir do recebimento da observação e da criação de cada
revisão ou sugestão. A partir do vencimento, o conteúdo deixa de ser exibido nas
telas e na API, mesmo se o agendador atrasar. A rotina automática elimina, em
lotes de até mil, o conteúdo e a identificação da fonte da observação, exclui as
revisões vencidas e limpa declaração e hash das sugestões vencidas. Uma referência
mínima da observação e sugestão é mantida para preservar relacionamentos; seus
identificadores derivados e hashes são eliminados, sem valores fictícios. Não se
afirma anonimização completa: datas e
autor continuam presentes. A limpeza e suas contagens são auditadas em transação;
uma falha de auditoria reverte as alterações. O agendador precisa estar ativo e
um volume grande pode demandar mais de uma execução.

**Limites importantes:** arquivos originais, backups e exportações antigas não
são apagados. Campos de fonte e evidência copiados para relações e registros da
auditoria imutável não são alterados pela rotina de retenção; podem conter dados
sensíveis e requerem controles próprios. Reimportar arquivo antigo pode recriar
os dados a partir da nova data de recebimento. A política não substitui a gestão
de retenção de todos os sistemas e cópias. Testes focados com dados fictícios
verificaram prazo, permissão, CSRF, ocultação, eliminação, idempotência e rollback.

## Proteção da auditoria em PostgreSQL e restauração

Foi identificada uma diferença real entre bancos: o SQLite já possuía gatilhos
contra alteração e exclusão direta dos registros de auditoria, enquanto o
PostgreSQL dependia apenas da proteção no modelo Django, que consultas SQL diretas
podiam contornar. A migração `0048` instala gatilhos PostgreSQL para UPDATE,
DELETE e TRUNCATE. A proteção exige permissões apropriadas: um proprietário da
tabela ou administrador do banco pode alterar ou desativar gatilhos; em produção,
use uma conta da aplicação com privilégios mínimos e administre migrações à parte.
Isso não equivale a imutabilidade contra um administrador privilegiado.

A restauração de backup em SQLite temporário também podia falhar quando IDs de
tipos de conteúdo e permissões diferiam entre o banco original e o banco novo. A
carga agora remove os registros criados pelas migrações **apenas no banco
temporário isolado**, antes de importar os do backup, dentro de uma transação.
Um teste PostgreSQL → SQLite passou com dados fictícios e verificação da cadeia.
Restauração **para** PostgreSQL permanece pendente.

Em PostgreSQL 16 descartável e sem portas publicadas, a suíte completa executou
642 testes, com três ignorados. Os testes de classes que fazem backup passaram a
usar base transacional nesse backend: isso exercita o backup fora da transação
externa, sem relaxar a exigência de isolamento. As alterações finais de retenção
e suas restrições posteriores a essa suíte foram testadas separadamente em ambos
os bancos. Na limpeza do banco PostgreSQL descartável de testes, o runner desativa
temporariamente apenas o gatilho de TRUNCATE e o restaura após o `flush`; essa
operação pertence exclusivamente aos testes, não à aplicação. A comunicação
local entre contêineres usou TLS desabilitado apenas no laboratório isolado.

## Pendências ainda abertas

Backtest com dados reais fornecidos pelo responsável, homologação de arquivos de
fornecedores e Jira/GLPI reais, retenção de cópias em outras fontes, desempenho
com tráfego e carga representativos, restauração para PostgreSQL e validação
independente do ajuste financeiro não são demonstrados pelos ensaios acima.
Não se introduziram pesos de EPSS, SSVC ou criticidade de serviço na fórmula
existente sem uma política quantitativa explícita e testes de validade.

## Verificações finais desta etapa

- `python manage.py test --noinput`: 646 testes em SQLite, oito ignorados;
  uma suíte anterior em PostgreSQL executou 642, com três ignorados. Depois das
  alterações finais, 20 testes dirigidos passaram em PostgreSQL.
- `ruff check .`, `mypy` no escopo de dois módulos do CI, `bandit` e
  `python manage.py makemigrations --check --dry-run`: concluídos sem achados
  novos. O Bandit registrou aviso informativo sobre um `nosec` existente.
- `pip-audit -r requirements.txt`: nenhuma vulnerabilidade conhecida encontrada
  na consulta realizada; o resultado depende das informações disponíveis no
  serviço consultado e não substitui a varredura da imagem.
- `pytest` com os argumentos de cobertura do CI: seis testes passaram, com
  cobertura de 25% no escopo selecionado **somente para essa suíte pytest**;
  esse número não mede a cobertura da suíte Django completa.
- `docker build -t sauron-pendencias:validacao .`: imagem construída localmente,
  utilizando camadas em cache. Não demonstra execução em produção ou ausência
  de vulnerabilidades; a varredura da nova imagem e a execução do CI remoto
  não foram verificadas nesta etapa.
- O cache das ferramentas precisou ser direcionado para diretórios temporários
  no contêiner de testes: as primeiras tentativas de lint e pytest com cobertura
  falharam por sistema somente leitura e ausência de plugin, respectivamente.
