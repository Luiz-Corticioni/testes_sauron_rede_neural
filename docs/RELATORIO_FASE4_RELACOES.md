# Sauron — Fase 4: relações de rede, identidade e negócio

**Data:** 02/11/2026. **Base:** aplicação completa da fase 3. **Migração:** `0025_relacoes_tipadas`. O pacote inclui as fases anteriores, código, testes e documentação. Nenhuma dependência de execução foi adicionada nesta fase.

**Validação final: 290 testes aprovados, sem falhas, em 108,538 segundos.** São 33 testes novos sobre os 257 da fase anterior. Ruff, Bandit, dependências compatíveis, migrações e configuração de produção passaram nas verificações descritas abaixo.

## Resultado e propósito

O Sauron passou a cadastrar relações direcionadas e documentadas entre ativos, separadas por camada e escopo. A web e o terminal oferecem alcance, menor caminho, ciclos e simulação de retirada de uma relação e/ou ativo. Há uma API JSON e links do caminho para cada evidência individual.

O objetivo é responder perguntas verificáveis: quais ativos aparecem ligados neste recorte? Qual o menor caminho registrado? O que deixa de ser alcançável quando um vínculo é retirado? A resposta depende do inventário e não demonstra exploração ou isolamento real.

O modelo matricial anterior continua usando suas dependências ponderadas. Não se alteraram CVSS, EPSS, KEV, estados de incidência, aceites, SLA ou resultados históricos por causa do grafo. As novas relações não recebem pesos de probabilidade inventados e não são criadas automaticamente a partir de pacotes SBOM ou dependências antigas.

## O que mudou e por quê

| Implementação | Motivo |
|---|---|
| Modelo `RelacaoAtivos` com origem, destino, tipo e escopo | Separar significados que um único vínculo genérico não consegue expressar. |
| Campos específicos por tipo, com validação no modelo e restrições SQL | Não aceitar identidade como se fosse porta de rede ou dependência de negócio como se fosse tráfego. |
| Fonte, evidência, observação, revisão e vigência | Explicitar de onde veio a relação e quando ela precisa de nova conferência. |
| Cadastro e revisão em serviço comum | Aplicar a mesma autorização e validação na web e no terminal. |
| Controle de versão ao editar | Bloquear sobrescrita de uma alteração feita enquanto outro operador preenchia o formulário. |
| Revogação com preservação do registro | Retirar o vínculo da análise sem apagar sua justificativa; revisões anteriores permanecem na auditoria. |
| Consulta sem cache do grafo | Revogações, vencimentos e baixa de ativos afetam a próxima análise. |
| Índice por camada/escopo/principal | Apoiar o recorte usado nas consultas, evitando depender apenas dos índices de origem/destino. |
| API, caminhos com evidências e acesso pelo Modo Euler | Fazer os cálculos usarem os cadastros reais e apresentar resultados que o operador consegue conferir. |
| Integração com contexto SSVC, backup e exportação | Manter decisões revisáveis e evidências restauráveis. |

Um erro de integração encontrado na suíte completa foi corrigido: o template inicialmente escolhido para o novo módulo tinha o mesmo nome do template compartilhado pelas listas antigas. O original foi restaurado; a nova tela usa `relacoes_tipadas.html`. As rotas de edição também seguem a convenção de nomes dos modelos usada pelo projeto. Os testes de regressão das páginas antigas voltaram a passar.

## Semântica das três camadas

Todas as setas são **origem → destino**, mas o significado varia:

| Camada | Significado | Campos obrigatórios específicos |
|---|---|---|
| REDE | A origem pode iniciar o tráfego declarado para o destino. | TCP/UDP e porta de destino de 1 a 65535, ou ICMP com porta 0. |
| IDENTIDADE | Há acesso declarado de um principal externo ao destino a partir do ativo de origem. | Principal exato e privilégio: leitura, execução ou administração. Não recebe protocolo/porta. |
| NEGOCIO | O ativo de origem fornece algo de que o destino depende. | Escopo e evidência do serviço/processo. Não recebe principal, privilégio ou protocolo/porta. |

**Identidade aqui é um atributo da relação entre ativos.** Pessoas, grupos, contas e delegações de diretório não são nós próprios nesta fase. Não há integração AD/Entra/LDAP nem coleta de sessões ou credenciais. Um principal cadastrado não cria usuário ou concede permissão no Sauron.

Cada análise exige uma única camada e um escopo exato. Identidade exige também o mesmo principal exato em todos os passos. Não se concatenam camadas, ambientes diferentes ou contas distintas. Ainda assim, concatenar relações de uma mesma camada é uma análise estrutural: tráfego A→B e B→C não comprova encaminhamento A→C; acesso do mesmo principal em dois vínculos não comprova disponibilidade ou reutilização de suas credenciais.

O desenho considera a distinção entre relações específicas de acesso encontrada na [documentação de arestas do BloodHound](https://bloodhound.specterops.io/resources/edges/overview) e no [repositório do projeto](https://github.com/SpecterOps/BloodHound). Não houve importação do seu código ou integração com seus coletores. O Sauron não oferece a cobertura de identidade do BloodHound.

A separação entre posição de rede e autorização também é coerente com o [NIST SP 800-207](https://csrc.nist.gov/pubs/sp/800/207/final), que não atribui confiança implícita à localização na rede. Nesta implementação, isso motiva não tratar uma conexão cadastrada como comprovação de acesso autorizado ou exploração.

## Matemática introduzida no Modo Euler

Para um grafo dirigido G e uma origem s:

- **Alcance R(s):** outros ativos para os quais existe um caminho dirigido. A origem não entra na contagem.
- **Menor caminho d(s,t):** menor número de arestas entre origem e destino, calculado por busca em largura (BFS). Em empate, a ordem de cadastro escolhe um dos caminhos; não se enumeram todos.
- **Grau de entrada/saída:** quantidade de ativos vizinhos distintos na base. Dois protocolos/portas para o mesmo destino preservam duas relações, mas contam um vizinho.
- **Cenário:** recalcula o alcance sem uma relação, sem um ativo, ou sem ambos. `Perdidos = R_base(s) − R_cenario(s)`. A retirada é apenas em memória.
- **Ciclos:** componentes fortemente conexas com mais de um ativo, usando Kosaraju iterativo. São grupos com caminhos de ida e volta, não necessariamente incidentes ou erros de arquitetura.

O cenário respeita relações paralelas e rotas alternativas. Remover uma porta não corta o caminho se outro vínculo elegível ainda o sustentar. Retirar um ativo antes alcançável inclui esse próprio ativo no total perdido, além dos destinos que ficaram sem caminho. Não se permite retirar a própria origem.

BFS e as duas passagens de Kosaraju percorrem listas de adjacência em O(V+E), sem matriz densa ou recursão. Ordenações e reconstrução dos caminhos exibidos têm custo adicional. Uma cadeia de 5.000 nós foi exercitada nos testes. Isso não constitui ensaio de carga com usuários concorrentes.

As definições de caminho dirigido e menor número de arestas podem ser conferidas na [documentação NetworkX de caminhos mínimos](https://networkx.org/documentation/stable/reference/algorithms/shortest_paths.html), e o algoritmo de componentes na [referência de Kosaraju](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.components.kosaraju_strongly_connected_components.html). NetworkX não foi adicionado como dependência: os algoritmos usados são pequenos e testados diretamente.

## Qualidade dos dados e limites de consulta

Entram na análise apenas relações vigentes, observadas até a data atual, com revisão **posterior** à data atual e ambos os ativos operacionais (ativo ou em manutenção). No início do dia indicado para revisão o vínculo já fica fora do cálculo. Observações futuras são rejeitadas no cadastro. Cadastros vencidos e revogados continuam acessíveis para conferência.

A análise conta todos os ativos operacionais do inventário como nós, inclusive os isolados. As arestas são somente as da camada/escopo/principal selecionados. O resultado informa relações no escopo, relações elegíveis e quantidade excluída. Não se deve interpretar um nó isolado como evidência de ausência de tráfego real.

| Limite | Comportamento |
|---|---|
| 10.000 ativos operacionais e 50.000 relações no recorte, incluindo as inelegíveis | Acima do limite, a consulta é rejeitada; não se calcula silenciosamente uma parte do inventário. |
| Destinos exibidos | Padrão 50; configurável de 1 a 100. O alcance total usa todo o recorte elegível. |
| Caminhos longos | Até 100 passos iniciais exibidos por caminho, com aviso. A distância preserva o valor completo. |
| Ciclos | Contagem completa; até 20 grupos e 50 ativos por grupo exibidos, com indicação de limite. |
| Evidências do resultado | Até 200 referências completas dos caminhos exibidos. Os demais IDs podem ser consultados individualmente. |
| Cadastro | Escopo, principal e fonte até 200 caracteres; evidência até 4.000. |

O SHA-256 apresentado identifica a representação do recorte consultado, incluindo data de corte e metadados. O cenário de retirada usa o mesmo hash de entrada. Esse hash não autentica fontes e não armazena sozinho uma cópia histórica do grafo. Para guardar o resultado, salve a resposta JSON da API e preserve exportações/backup e auditoria conforme sua política.

## Segurança e permissões

Consultar lista, detalhe, painel ou API exige `view_ativo` e `view_relacaoativos`. Cadastro exige adicionalmente `add_relacaoativos`; edição/revogação exige `change_relacaoativos`. Não há permissão padrão de exclusão nem rota de exclusão do módulo. As referências a ativos e autores usam proteção contra exclusão em cascata.

O serviço relê a conta ativa e suas permissões dentro da transação de gravação. Campos de autoria, IDs e timestamps não podem ser injetados pelo formulário ou pelo contrato do serviço. O terminal revalida acesso após a confirmação; uma conta desativada durante a entrada não consegue gravar.

As novas rotas seguem o MFA da aplicação. Permissões de cadastro/edição fazem a conta exigir TOTP, mesmo sem ser staff. Usuários comuns continuam bloqueados na administração de usuários/grupos. Relações de identidade são dados do inventário, sem efeito nessas autorizações.

Gravações web exigem POST e CSRF; GET apenas consulta ou apresenta formulário. A API de análise aceita GET e não altera cadastros. Textos externos são escapados nos templates. Fonte/evidência não são buscadas pela rede e nenhum comando de scanner é executado. A simulação de retirada não revoga regras de firewall ou acessos reais.

Os grupos oficiais continuam obedecendo à política existente: Gerentes podem cadastrar/editar relações; Auditores e Operadores podem consultá-las. `preparar_servidor` atualiza esses grupos por meio de `configurar_grupos`. Contas com papéis personalizados precisam receber explicitamente as novas permissões. Esse comando reaplica a política oficial dos grupos; confira eventuais personalizações prévias.

## SSVC, auditoria, exportação e backup

Criar ou revisar uma relação gera evento de auditoria com ator e dados. Uma decisão SSVC de ativo relacionado passa a registrar apenas um hash do conjunto de relações, sem copiar principal, fonte ou evidência para o contexto visível a quem só pode ler SSVC.

Alterações, revogação, expiração ou mudanças de estado nos ativos envolvidos podem pedir reavaliação SSVC; o resultado histórico não muda. O hash é calculado progressivamente, em lotes, para evitar carregar todos os textos das relações na memória do contexto. Ativos sem relações novas mantêm a estrutura de contexto anterior, evitando invalidar decisões só pela instalação da fase.

`inventario_completo` inclui a coleção `relacaoativos`. O backup lógico cifrado inclui relações e autores; a restauração foi verificada. A exportação legada de quatro arquivos JSON conserva seu contrato e não substitui a exportação completa.

Ao atualizar um banco ainda no schema 0024, o backup aceita a ausência da tabela nova antes de aplicar 0025. Foi exercitada a restauração desse backup anterior no schema atual. SBOM, PURL, conteúdo e hash da fase 3 foram preservados. Nenhuma relação foi inventada durante a migração.

## Verificação realizada

Os 33 testes novos cobrem direção, distâncias, origem fora da contagem, destinos isolados, caminhos alternativos, relações paralelas, retirada de ativo/elo, ciclos, cadeia longa, limites, regras por camada, datas, unicidade, restrições SQL, edição concorrente, autoria, permissões revogadas, MFA, CSRF, escape de HTML, respostas de erro, ausência de chamadas externas, conexão dos links com as evidências, papéis oficiais, SSVC, backup/restauração e equivalência web/API/terminal.

Além da suíte completa, foram executados:

| Verificação | Resultado |
|---|---|
| Ruff e Bandit | Sem ocorrências; não equivalem a prova de ausência de vulnerabilidades. |
| `pip check` | Dependências compatíveis; nenhuma nova biblioteca de execução nesta fase. |
| `makemigrations --check --dry-run` | Nenhuma alteração de modelo sem migração. |
| Check Django de produção e `collectstatic` | Aprovados. |
| Atualização de schema 0024 → 0025 | Dados de ativo, PURL, SBOM e CVE preservados em SQLite descartável. Backup anterior restaurado com auditoria validada. |
| Fluxo com `DEBUG=0` | Login/TOTP; formulário com CSRF validado; gravação SQL; painel, API, caminho e evidência individual; cenário sem mutação; revogação refletida na consulta seguinte. |
| Integrações anteriores no fluxo de produção simulado | EPSS com resposta simulada, SSVC, upload/download SBOM/VEX, cookies seguros e estáticos mantidos. |

Evidências estão em `docs/evidencias/fase4_relacoes/`. Mensagens de falha de e-mail e HTTP 503 no log da suíte são cenários simulados deliberadamente.

Não houve homologação com PostgreSQL real, TLS real, SMTP real, firewall, AD/Entra/LDAP ou ambiente externo de produção. O cliente Django simula HTTPS; não verifica certificados ou infraestrutura. O isolamento de leituras simultâneas e o dimensionamento precisam de homologação no banco real. A auditoria online de vulnerabilidades das dependências permanece pendente por indisponibilidade de DNS do ambiente; `pip check` não a substitui.

## Atualização e uso

1. Pare os serviços, gere backup cifrado com a versão instalada e preserve banco/configurações/chaves.
2. Extraia a aplicação completa em pasta nova. No ambiente virtual, execute `python -m pip install -r requirements.txt` para manter a base correta.
3. Execute `python manage.py preparar_servidor`: migração 0025, grupos oficiais e estáticos. Revise a implantação com `python manage.py verificar_implantacao --json`.
4. Na navegação, abra **Relações por camada**, cadastre relações com fonte, evidência e datas. **Editar ou revogar** preserva o registro. O detalhe mostra autoria e evidência atual.
5. Abra **Analisar alcance e cenários**, escolha camada, escopo, origem e, se necessário, principal/destino. A retirada simulada é opcional e não grava alterações.
6. No terminal, use opção **9** do menu operacional para lista/cadastro/revisão/análise, ou opção **8** do Modo Euler para análise. Na web, o Modo Euler também tem um acesso direto ao grafo, condicionado às novas permissões.

API: `/api/grafo-relacoes/?tipo=REDE&escopo=homologacao&origem=CODIGO&limite=50`. Parâmetros opcionais: `destino`, `remover_relacao` e `remover_ativo`; a camada IDENTIDADE exige `principal`. Autenticação, MFA e permissões também se aplicam à API. Os códigos devem ser os IDs reais dos ativos cadastrados.

Um roteiro de homologação sem dados reais está em `docs/exemplos/roteiro-grafo-relacoes.md`.

## Avaliação crítica e próximos passos

O projeto ganha relações explicáveis e resultados estruturais conferíveis. Ainda não é um motor de caminhos de ataque com pré-condições de exploração. Não há verificação de credencial, contexto de sessão, grupos, delegação, regras de negação, direção de resposta stateful, NAT, regras temporais de firewall, segmentação efetiva ou explorabilidade de CVE ao longo do caminho.

Uma relação falsa com evidência escrita de forma convincente continua falsa. Datas e auditoria ajudam a responsabilizar e revisar; não substituem coleta confiável. Sem processo de revisão, o grafo pode ficar incompleto ou excluir relações vencidas que continuam existindo no mundo real. Ausência de caminho no banco não é um certificado de segurança.

A evolução seguinte deve acrescentar qualidade e cobertura das evidências, identidades como nós próprios e pré-condições de acesso. Cortes mínimos e cenários de contenção são candidatos posteriores; exigem definir corretamente o que cada remoção representa e seu custo operacional. Somar mais métricas antes disso aumentaria a aparência de precisão sem melhorar a decisão.
