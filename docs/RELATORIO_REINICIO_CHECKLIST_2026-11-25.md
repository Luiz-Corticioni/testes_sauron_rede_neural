# Reinício e checklist do Trabalho 2 — 25/11/2026

## Alterações

O Compose usa `restart: always` para os serviços web e agendador. A tarefa
`preparar` conserva `restart: no`. Se um operador parar um container, `always`
permite que ele volte quando o daemon reiniciar; `unless-stopped` preservava a
parada manual também após reinício do daemon. Isso não recria containers removidos
por `compose down` e requer Docker habilitado e ativo no boot. A alteração só
atinge containers depois de recriados pelo `docker compose up -d`.
Os serviços opcionais PostgreSQL e proxy HTTPS também receberam `always`; não
foram submetidos ao mesmo ensaio de falha desta etapa.

O CI recebeu teste que encerra o processo principal dentro de cada container,
verifica o contador de reinícios e, na web, verifica HTTP e preservação de arquivo
no volume. O teste não reinicia o daemon ou host. Liveness HTTP não verifica toda
a aplicação, e `unhealthy` sozinho não dispara a política de restart.

## Ensaio local

Imagem `sauron-reinicio:teste` construída no Docker Desktop Linux com camadas em
cache. Projeto Compose descartável com volume e `.env` próprios e porta 2239:
preparação terminou com código 0; web e agendador ficaram saudáveis. `seed_demo
--empresa` criou 31 ativos fictícios. Após interrupção do processo principal
de cada serviço dentro do respectivo container, ambos voltaram a `running`,
cada contador `RestartCount` aumentou de 0 para 1, a rota `/api/saude/`
respondeu e os 31 ativos permaneceram no banco. O teste usou SQLite e não
simulou falha de disco, indisponibilidade de PostgreSQL ou reinício do host.
Depois de `compose down` sem `-v` e novo `up -d --no-build`, os 31 ativos
continuaram no volume. A suíte focada `tests.test_sprint_conformidade`,
`tests.test_preparacao_banco`, `tests.test_implantacao` e `tests.test_regressao`
executou 15 testes, sem falhas, em container sem rede.
`docker compose config --quiet` validou as configurações faculdade, HTTPS e
PostgreSQL com valores de teste; isso verifica sintaxe, não o serviço real.

Uma primeira tentativa usou `docker compose kill`: ela foi tratada como parada
manual e não reproduziu uma falha espontânea. A tentativa de sinalizar PID 1 do
namespace também não provocou a falha; o ensaio correto encerrou o filho do
`docker-init`. Esses resultados não foram descartados como sucessos.

## Checklist recebido

- Objetos, herança e polimorfismo: hierarquia educacional e testes existentes;
  demonstração e domínio pessoal precisam ser apresentados pelo aluno.
- Persistência: banco SQL operacional e exportação JSON; catálogo educacional
  usa JSON. O enunciado/checklist sobre persistência JSON admite interpretação a
  esclarecer com o docente; não afirmar que o site usa quatro arrays como banco.
- Risco próprio e efetivo: modelo linear e exemplo pequeno existente em
  `tests/test_sprint_conformidade.py`; estabilidade, singularidade e precisão
  exigem os testes e explicação do modelo, não somente exibir uma tela.
- Container e persistência: ensaio local acima, não uma validação de produção.
- Requisitos do Trabalho 1: sem o enunciado completo, conformidade integral não
  verificada. Permissão de acesso ao repositório pelo docente: não verificada.
- Servidor da faculdade: reboot real, ativação do daemon no boot e 24 horas
  contínuas não foram observados. Use `scripts/prova_24h.py` e
  `scripts/verificar_disponibilidade.py` conforme `DOCKER_TRABALHO_2.md`.
  Não é possível garantir funcionamento futuro ou afirmar essas evidências.

## Operação

Confira `systemctl is-enabled docker` e `systemctl is-active docker` com o
administrador; rootless e Docker Desktop têm inicialização diferente. Uma
aplicação saudável na liveness pode ainda ter falhas no banco ou em integrações;
verifique também o inventário e o agendador. Não use `down -v` para parar o
serviço com dados que queira preservar. Preparação chama `configurar_grupos`,
que pode redefinir permissões dos grupos padrão; instalações customizadas
exigem revisão prévia. Nenhuma alteração de serviço do host foi executada aqui.
