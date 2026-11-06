# Trabalho 2 — rastreabilidade e alterações

Revisão de 05/11/2026, baseada no enunciado e no arquivo `sprints.txt` recebidos.
Status indicam o que foi demonstrado nesta revisão, não uma nota do professor.
Os requisitos do Trabalho 1 e os cards completos das Sprints 3 e 5 não foram
fornecidos; não é possível confirmar requisitos que constem apenas neles.

## Requisitos do enunciado

| Requisito | Evidência e situação |
|---|---|
| Objetos, herança e polimorfismo (20%) | `dominio/equipamentos.py`: fábrica de subclasses, `exibir_detalhes` e `fator_exposicao`; testes reconstroem Servidor e Notebook. |
| Persistência JSON/SQL (20%) | Site e CLI usam SQL relacional; exportação explícita gera quatro arrays JSON com IDs e vínculos. Catálogo didático agora grava/recarrega ativos diretamente em JSON. **Parcial:** não é uma aplicação web inteiramente persistida em arrays JSON; confirme a interpretação do enunciado com o professor. SQL é a fonte de verdade operacional. |
| Container por 24 horas no servidor (45%) | Dockerfile, Compose, volume, healthcheck e monitor existem. **Pendente:** build e execução reais, persistência/reboot e observação contínua por 24h no servidor do professor. Sem essas evidências não se pode afirmar que o requisito está cumprido. |
| Modelo linear (15%) | `matematica/risco.py` usa perfil puro: `M`, vetor CVSS `v`, `b=Mv` e `(I-A)x=b`. O teste `test_equacao_com_solucao_calculada_a_mao` verifica `[8,0,0]` e `[8,4,1.8]`. O sistema rejeita matrizes fora das condições de estabilidade implementadas. |

Para uma dependência de B sobre A com peso 0,5, `A[B,A]=0,5`; o risco de A
contribui para B. O perfil operacional acrescenta fatores e não deve ser confundido
com o modelo puro cobrado. Risco é um índice dependente de premissas, não previsão
de comprometimento. O projeto de referência foi consultado como inspiração para
organização e apresentação: https://github.com/SmokyyeSZ/Inventario-Ativos-TI.
O código e os dados do outro projeto não foram copiados; o enunciado proíbe entregas
iguais entre alunos e exige que o aluno entenda e explique suas decisões.

## Cards da Sprint 4

| Card | Situação após esta revisão |
|---|---|
| S4_01 camadas | Presente: `ARQUITETURA.md`, domínio, aplicação, infraestrutura, web e CLI. O acesso operacional ao ORM continua direto em partes da aplicação. |
| S4_02 SOLID | Parcial: interface `Repositorio`, implementações JSON e memória e `CatalogoEducacional` trocável testados; a aplicação web completa não foi refatorada para essa interface. |
| S4_03 padrões | Presente no catálogo didático: fábrica `Equipamento.from_dict`, Repository e estratégias `por_nome`/`por_tipo`. Não se usa Singleton para arquivo, pois estado global complica isolamento e concorrência. |
| S4_04 JSON | Parcial: gravação atômica por arquivo, validação de array de objetos e reconstituição de subtipos. Há exportação e teste de vínculos SQL→JSON; o fluxo web permanece SQL e não grava automaticamente os quatro arrays. A escrita atômica individual não torna quatro arquivos uma transação única. |
| S4_05 serviço | Presente no código: HTTP Django, endpoint `/api/saude/`, cliente `scripts/healthcheck.py` e diagrama em `ARQUITETURA.md`. Continuidade real requer execução. |
| S4_06 SQL e JOIN | Parcial: migrações criam o esquema; `consultas_sprint.py` executa LEFT JOIN e agregação parametrizada sobre tabelas reais. `python manage.py sqlmigrate inventario 0001` mostra SQL da primeira migração; não há script SQL consolidado para todas as migrações e todos os bancos. |
| S4_07 relatórios SQL | Presente: `python manage.py relatorio_sql_sprint --limiar 0` gera contagem e soma CVSS por ativo com incidências abertas/em tratamento/aceitas. Cobertura de outros relatórios solicitados pode exigir ampliação. |
| S4_08 hash e índices | Parcial: hash encadeado, teste de colisão, PK de ativo e CVE único; `benchmark_sprint.py` compara buscas e `EXPLAIN QUERY PLAN` antes/depois de índice em banco sintético, não no banco de produção. |
| S4_09 árvore binária | Presente para estudo: inserção, busca, quatro percursos, testes e alturas. Chaves duplicadas são ignoradas: para preservar vulnerabilidades de mesmo CVSS seria preciso chave composta. Não é índice de produção balanceado. |
| S4_10 grafos | Presente: BFS em `grafo.py`, DFS e ciclos em `algoritmos_sprint.py`; `relatorio_sprint` percorre dependências a partir dos ativos marcados como expostos. Alcance estrutural não prova rota explorável. |
| S4_11 Merge Sort | Presente e testado: ordenação estável e ranking real por risco em `relatorio_sprint`. Não substitui `sorted()` no caminho normal da aplicação. |
| S4_12 Quick Sort | Presente em escopo didático: Lomuto com pivô final ou aleatório, testes e comparação em entradas aleatória e crescente. São medições simples, não um estudo estatístico. |
| S4_13 complexidade | Parcial: medições sintéticas de 10/100/1000 ativos e cProfile, além de comparação de buscas/ordenação. Uma única amostra não caracteriza escalabilidade nem permite concluir uma lei cúbica para implementação esparsa. |
| S4_14 pytest | Presente em escopo limitado: `testes_pytest/`, cobertura e etapa CI; a suíte principal é Django/unittest. Não há cobertura pytest completa de todo o sistema. |
| S4_15 Docker básico | Parcial: roteiro em `DOCKER_TRABALHO_2.md`; faltam comandos executados e evidências em um host com Docker. |
| S4_16 imagem | Parcial: Dockerfile e `.dockerignore`; build e container não foram executados neste ambiente. |
| S4_17 Compose | Parcial: `compose.yaml` configura volume, política de reinício e healthcheck; faltam testes reais de reinício e persistência. |
| S4_18 logs | Parcial: logs dos processos, rotação do driver Docker e monitor de disponibilidade; coleta contínua no ambiente real ainda não ocorreu. Nem todas as saídas são logs estruturados JSON da aplicação. |
| S4_19 servidor Linux | Pendente: acesso, implantação e comprovação após reinicialização do servidor indicado pelo professor. |
| S4_20 integração | Parcial: repositório, código, testes e roteiro abaixo; faltam as 24 horas e validações de container/servidor. |

## O que mudou e por quê

- Corrigido o coletor que procurava `sauron-apogeu`, nome não definido pelo Compose:
  agora descobre o container do serviço e recusa misturar evidências em arquivo já existente.
- `.gitattributes` fixa finais LF nos scripts de shell; `.dockerignore` exclui bancos,
  logs, ambientes virtuais e caches comuns, reduzindo risco de incluí-los na imagem.
- A validação do repositório rejeita arrays que contenham itens que não sejam objetos;
  o repositório em memória copia dados para evitar mutações acidentais por referência.
- Catálogo educacional demonstra inversão de dependência, fábrica e estratégia. Ele é
  isolado, para não manter cópias JSON automaticamente divergentes do banco operacional.
  Seu método de cadastro é didático, não oferece controle de concorrência e não deve
  ser usado como substituto multiusuário do ORM.
- Adicionados estruturas e algoritmos de estudo, relatórios em banco, suíte pytest e
  testes de integração para risco, SQL, persistência e descoberta do container.
- O guia Docker explica preparação, primeiro administrador, acesso, volume, reinício
  e prova de 24 horas sem tratar configuração como evidência operacional.

## Verificações realizadas

- Suíte principal Django: 386 testes passaram; após pequenos ajustes nas estruturas
  didáticas e validação JSON, os testes de conformidade e regressão foram repetidos:
  11 testes passaram. Pytest: seis testes passaram.
- A cobertura pytest foi 28% dos módulos selecionados no comando documentado, não
  de toda a aplicação. A suíte Django cobre outros caminhos que não entram nessa medição.
- `ruff check .`, `pip check`, verificação de produção e `makemigrations --check
  --dry-run` passaram. O YAML do Compose e alguns campos foram conferidos estaticamente;
  isso não substitui `docker compose config`, build ou execução real.
- As respostas 503 das integrações externas e a falha de envio SMTP na suíte são
  cenários simulados pelos testes; esta execução não comprova envio de e-mail real.

## Resultados reproduzíveis de desempenho

Execute `python scripts/benchmark_sprint.py`; ele não usa nem altera a base real.
Na execução Windows/Python 3.12 desta revisão, uma lista de 1.000 itens demorou
aproximadamente 1,35 ms em Merge, 0,70 ms em Quick e 0,049 ms em `sorted()`; uma
árvore com 500 chaves teve altura 500 na inserção crescente e 20 na embaralhada.
Em 100 consultas de uma tabela sintética SQLite com 10.000 linhas, o plano mudou
de `SCAN` para `SEARCH ... USING INDEX`, de cerca de 22 ms para 0,27 ms no total.
Com 10/100/1000 ativos em cadeia esparsa e uma vulnerabilidade, o cálculo foi cerca
de 2,27/2,19/2,40 ms; construção do modelo ficou fora da cronometragem. Os tempos
são amostras individuais, sensíveis a máquina, cache e perfilamento e não são SLA.
Não comparar diretamente com O(n³): os caminhos esparsos e densos são diferentes.

| Operação | Custo típico | Limitação |
|---|---|---|
| Hash | Busca média O(1) | Colisões podem chegar a O(n); hash de tabela não é hash de senha. |
| Árvore binária | O(h) | Sem balanceamento, altura h pode ser n. |
| BFS/DFS | O(V+E) | Modelo estrutural depende das arestas cadastradas. |
| Merge Sort | O(n log n) | Espaço adicional O(n), estável. |
| Quick Sort Lomuto | Média O(n log n), pior O(n²) | Pivô final degrada em entrada ordenada; não é estável. |

## Roteiro de apresentação em cinco minutos

1. **0–1 min:** problema, camadas e ativos com duas subclasses diferentes.
2. **1–2 min:** crie ou mostre um ativo, vulnerabilidade e incidência; explique SQL,
   depois exporte os quatro arrays e mostre IDs e vínculos sem expor dados reais.
3. **2–3 min:** mostre `M`, `v`, `A`, `b` e o exemplo `[8,4,1.8]`; a seta do
   fornecedor aponta para o dependente. Mostre o ranking e explique as premissas.
4. **3–4 min:** execute testes, mostre Repository/Factory/Strategy e alcance do grafo.
5. **4–5 min:** apresente imagem/container/volume e evidências reais do servidor;
   declare claramente o que não foi comprovado ou não foi implementado.

Antes da entrega, ensaie com seus próprios dados sintéticos e entenda cada comando.
