# Sprint 5 — verificação, alterações e pendências

[Início](../README.md) · [Índice](README.md) · [Segurança e arquitetura](SPRINT5_SEGURANCA_ARQUITETURA.md) · [Contrato OpenAPI v1](openapi-v1.json)

Data: 13/11/2026. Esta revisão usa a branch `sprint5-conformidade`, que parte da versão com a interface mais recente. “Parcial” significa que ainda faltam requisitos ou evidências; nenhum item presencial ou de servidor é dado como realizado apenas porque existe código. Os conteúdos de estudo e os exercícios não são automaticamente comprovados pela aplicação.

| Card | Situação | Evidência e trabalho restante |
|---|---|---|
| S5_01 Refatoração | Parcial | Domínio já usa polimorfismo (`inventario/dominio/equipamentos.py`); tipagem e mypy foram adicionados para duas classes de domínio. A CI verifica esses dois arquivos, não o projeto inteiro. Foram feitos extração de função (`ab4617a`), renomeação (`653d2ba`) e movimentação para o módulo de tipos (`7a412d8`), em commits separados, com testes. A extração foi sobre a nova consulta v1; as demais alterações foram no domínio existente. A dívida restante foi registrada nas issues abaixo. |
| S5_02 OWASP | Parcial | [Análise de segurança](SPRINT5_SEGURANCA_ARQUITETURA.md) usa a edição 2025; `pip-audit -r requirements.txt` não encontrou vulnerabilidades conhecidas na execução local. Achados Docker reais ainda precisam ser avaliados e cadastrados no inventário autorizado; não foram atribuídos CVSS fictícios. |
| S5_03 REST | Parcial | Foram adicionados `/api/v1/ativos/` e `/api/v1/vulnerabilidades/{id}/ativos/`, com paginação, filtro, ordenação de risco e Problem Details nas falhas tratadas. A API v1 é somente de leitura: ainda não há CRUD REST, Location, validação de corpo ou padronização das APIs antigas. |
| S5_04 OpenAPI | Parcial | [Especificação 3.1](openapi-v1.json) descreve somente as duas rotas v1 e foi validada; a validação também está no workflow. Falta documentar as rotas legadas e disponibilizar Swagger UI integrado e testes de contrato mais amplos. |
| S5_05 Mapeamento ORM | Parcial | [Diagrama e explicação](SPRINT5_SEGURANCA_ARQUITETURA.md) descrevem ORM Django, associação N:N e herança. Um teste mostra 3 consultas versus 1 com `select_related` para dois ativos. Falta uma avaliação completa de N+1 em todas as telas. |
| S5_06 ORM relacional | Parcial | Persistência operacional usa ORM Django e migrações Django, com testes SQLite. SQLAlchemy/Alembic não foram acrescentados como segunda persistência paralela; não há prova de intercambialidade transparente com o repositório JSON educacional. |
| S5_07 Injeção SQL | Parcial | ORM usa parâmetros; consulta SQL manual em `consultas_sprint.py` usa parâmetros. Teste v1 trata payload de busca como texto, e Bandit foi executado. Demonstração vulnerável separada em laboratório ainda não foi produzida; revisão não constitui prova de ausência de falhas. |
| S5_08 Senhas | Parcial | Argon2id é o novo padrão; testes cobrem sal e atualização de PBKDF2 existente. Política está no documento de segurança. Há benchmark educativo em `scripts/benchmark_senhas.py`; falta revisão completa de vazamento de credenciais em todos os logs. |
| S5_09 API keys/JWT | Pendente | Sessão Django com MFA e permissões é usada na web e API; não existe API key, JWT, revogação nem testes correspondentes. Sessão não é equivalente ao entregável literal. Um mecanismo para integração deve ser projetado sem contornar MFA ou expor chaves. |
| S5_10 Sessões e autorização | Parcial | Grupos, permissões por rota/serviço, expiração, CSRF, cookies e testes existem; matriz e limites em [segurança](SPRINT5_SEGURANCA_ARQUITETURA.md). Não há isolamento por organização/usuário para todos os objetos; papéis com leitura podem ver o inventário compartilhado. Não alegar multitenancy ou cobertura exaustiva. |
| S5_11 TLS | Parcial | `compose.https.yaml` oferece Caddy, HTTPS automático e proxy; configuração de HSTS e redirecionamento depende de produção. Sem domínio, acesso e execução reais não há evidência `openssl s_client` ou TLS negociado. |
| S5_12 Testes API | Parcial | Há testes de autenticação, MFA, permissões, filtro, injeção, paginação e erros da v1 na suíte Django/CI. Faltam CRUD API e Schemathesis; `tests/test_api_v1_sprint5.py`. |
| S5_13 Git/release | Parcial | Trabalho isolado em branch e commits separados. Não foram comprovadas proteção da main, release v1.0.0, hotfix, revisão por PR ou changelog completo. Não mudar configurações globais sem verificar o repositório e suas consequências. |
| S5_14 CI/CD | Parcial | CI testa aplicação e instalação, executa Bandit/pip-audit, constrói e varre imagem; a política de Trivy não foi desativada. Publicação no GHCR, implantação por SSH e rollback automático não foram implementados ou testados. Não há servidor autorizado para deploy automático. |
| S5_15 Hardening | Parcial | Compose existente usa usuário sem privilégios, root filesystem somente leitura, `cap_drop`, `no-new-privileges` e limites. A imagem base foi atualizada e aplica atualizações disponíveis no build. As comparações reduziram os registros do Trivy de 139 para 98 e depois 47 (todos altos, nenhum crítico), mantendo falha no scan. Falta classificar e tratar o risco remanescente. SSH, firewall e atualizações do servidor não foram alterados. |
| S5_16 Nuvem | Pendente | Não foi escolhida ou criada conta/provedor; custos, responsabilidades reais e configurações de MFA e alertas não foram comprovados. Não criar recursos pagos automaticamente. |
| S5_17 Publicação na nuvem | Pendente | Sem registro de imagem publicado, serviço em nuvem, HTTPS real ou evidência de encerramento. O usuário pediu para não se preocupar com acesso ao servidor por enquanto. |
| S5_18 Arquitetura | Parcial | Há [arquitetura e ADRs existentes](ARQUITETURA.md); diagrama de contexto e STRIDE inicial estão no documento de segurança. Faltam modelo C4 de componentes completo e revisão das ameaças com responsáveis. |
| S5_19 Apresentação | Parcial | Há [roteiro e dez perguntas](SPRINT5_APRESENTACAO.md), guia e dados demonstrativos. Ainda não há gravação, revisão de slides, ensaio com colega ou comprovação de tempo. |
| S5_20 Servidor compartilhado | Parcial | Matrícula `12621CBS228`, identificação `trab02_2026_2_12621cbs228` e porta 2228 em `compose.faculdade.yaml`; guia detalha volume e risco de migração. O endereço SSH informado é de rede local e o usuário pediu para deixar o acesso para depois. Não há implantação ou prova de 24 horas. O nome do repositório GitHub não foi alterado. |
| S5_21 Review e retrospectiva | Pendente | A entrega exige demonstração real, feedback do professor/colegas, retrospectiva e aprendizados pessoais; não podem ser inventados. A tabela e o backlog servem como preparação. |

## Como usar a API v1

Entre pela interface e conclua o MFA antes de usar o navegador ou um cliente HTTP com a mesma sessão. A URL `GET /api/v1/ativos/?pagina=1&tamanho=25&busca=servidor&ordenar=nome` retorna página, total e resultados. `ordenar=-risco` usa o risco efetivo do perfil puro e exige as quatro permissões de leitura do modelo; o valor representa pontos, não probabilidade. A ordenação calcula/carrega o risco do inventário e pode ser cara em bases grandes. `GET /api/v1/vulnerabilidades/VUL-RCE-0001/ativos/` lista incidências vinculadas, inclusive status que não necessariamente representam risco ainda aberto.

Cada consulta exige permissões próprias. Sem sessão, a v1 retorna 401; sem MFA ou permissão, 403; parâmetros inválidos, 422. As rotas legadas mantêm seus formatos anteriores. O arquivo OpenAPI pode ser importado em uma ferramenta local; não envie cookies ou dados reais a editores externos. Uma página de consulta acessível em `/api/v1/docs/` oferece um formulário de busca e um link para o contrato servido em `/api/v1/openapi.json`; ela não equivale ao Swagger UI. A especificação não cobre o conjunto antigo da API.

## Evidências de verificação

- Antes das mudanças: 407 testes Django passaram na branch visual, no Windows local com SQLite.
- Após as alterações, a suíte completa passou com 417 testes no Windows local e SQLite. Após Argon2, 37 testes de senha, acesso e MFA passaram; foram testadas senhas distintas com mesmo texto e atualização de hash PBKDF2.
- Mypy 2.4.1 com `--check-untyped-defs --follow-imports=silent --ignore-missing-imports` passou para os dois arquivos explicitados no workflow. Isso não demonstra tipagem integral.
- O benchmark educativo executou SHA-256 e Argon2id no Windows local, sem senha real; as medianas foram 0,000600 ms e 42,63 ms respectivamente, em amostras de tamanhos diferentes. Não é teste de carga nem garante capacidade do servidor.
- A especificação OpenAPI foi validada com `python -m openapi_spec_validator docs/openapi-v1.json`.
- Bandit terminou sem achados reportados e emitiu aviso de `nosec` preexistente. `pip-audit` não encontrou vulnerabilidades conhecidas em `requirements.txt` em 13/11/2026; a conclusão pode mudar com novas publicações.
- Docker não estava disponível nesta máquina. O build e a inicialização foram executados no GitHub para o commit `753ddd6`, mas o scan encontrou 47 registros altos. O resultado da CI deve ser conferido para o commit final, incluindo o job `imagem`.

## Backlog priorizado

1. **P1 — Imagem e implantação:** conferir o novo scan Trivy, atualizar componentes com correção e analisar aplicabilidade/exceções de CVEs sem correção; registrar antes/depois e evitar desativar o bloqueio.
2. **P1 — API:** definir contrato de escrita, validação, permissões por operação e CSRF; implementar CRUD pelos serviços existentes e testar persistência, concorrência e erros.
3. **P1 — Integração máquina a máquina:** decidir necessidade de API keys/JWT, ciclo de vida, revogação, escopo e relacionamento com MFA; não tratar um token não revogável como melhoria automática.
4. **P2 — Documentação/testes:** ampliar OpenAPI e testes de contrato, instalar UI local segura, medir mypy e cobertura além dos dois módulos.
5. **P2 — Entregáveis operacionais:** após autorização, testar TLS, volume e restauração no servidor; coletar 24 horas reais e verificar coexistência de portas/volumes.
6. **P2 — Governança:** configurar proteção de branch, PR, changelog e releases de modo compatível com o repositório; definir responsáveis pelas issues registradas.
7. **P3 — Acadêmicos/presenciais:** preparar slides, gravação, revisão, feedback, retrospectiva e análise de custos da nuvem com valores reais e datados.

## Issues registradas

- [#13 — Imagem Docker e vulnerabilidades](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/issues/13)
- [#14 — API, testes e documentação](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/issues/14)
- [#15 — Autenticação para integrações externas](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/issues/15)
- [#16 — Implantação na faculdade e evidências](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/issues/16)
- [#17 — Governança e apresentação](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/issues/17)

## Comparação inicial da imagem

Na [execução anterior](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/actions/runs/43349053827) o Trivy identificou 139 registros (130 altos e 9 críticos). Com a base Bookworm atualizada e atualização de pacotes, a [execução comparativa](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/actions/runs/43466814637) identificou 98 registros (96 altos e 2 críticos). Ambas as varreduras incluíram vulnerabilidades sem correção disponível; contagens dependem do banco do Trivy e não demonstram exploração efetiva. Na [comparação com Debian Trixie](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/actions/runs/43467814587), o build e a inicialização passaram e o Trivy encontrou 47 registros altos e nenhum crítico. A política reprovou o job, pois continua incluindo gravidade alta. A execução se refere ao commit `753ddd6`; o commit final deve ser conferido separadamente.
