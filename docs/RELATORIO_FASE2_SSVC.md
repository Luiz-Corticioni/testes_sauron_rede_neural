# Fase 2 — SSVC Deployer por ocorrência

Data: 02/11/2026. Esta entrega acrescenta SSVC à aplicação completa da fase 1. EPSS e os controles anteriores foram preservados. A implementação é uma representação local da tabela Deployer consultada no CERT/CC, não uma nova versão oficial ou certificação desse projeto.

**Validação final: 229 testes aprovados, zero falhas, em 81,715 segundos.** São 19 testes novos sobre os 210 anteriores; um deles confere as 72 combinações da tabela. Ruff, Bandit, dependências compatíveis, migrações e check Django de produção aprovados.

## Resultado e propósito

O operador pode avaliar a prioridade de uma remediação/mitigação para uma ocorrência implantada, justificar suas respostas e consultar o histórico pela web ou pelo terminal. A aplicação calcula a ação pela tabela; o cliente não escolhe o resultado. **SSVC não muda automaticamente status, aceite de risco, prazo de correção ou SLA.**

A fonte consultada tem 72 combinações de Exploitation, System Exposure, Automatable e Human Impact. O arquivo local identifica os pontos e suas versões, a origem, a data da consulta e o identificador local `certcc-deployer-snapshot-2026-11-02`. Cada avaliação guarda o SHA-256 da tabela utilizada. O SDK original não foi adicionado como dependência.

Fonte funcional e atribuição: CERT Coordination Center / Carnegie Mellon University, [tabela Deployer](https://certcc.github.io/SSVC/howto/deployer_tree/), [repositório SSVC](https://github.com/CERTCC/SSVC). As saídas oficiais preservadas são defer, scheduled, out-of-cycle e immediate. “Pendente de contexto” é um estado do Sauron para ausência de respostas, não uma quinta ação oficial.

## O que mudou e por quê

| Mudança | Motivo |
|---|---|
| Tabela local explícita com 72 linhas | Evita redesenhar a decisão por pesos arbitrários ou uma cadeia extensa de condicionais. Funciona sem rede e permite verificar cada combinação. |
| Avaliador puro com validação de completude, entradas e versão | Uma tabela incompleta, resposta inválida ou versão não suportada é recusada. Resposta ausente não vira “baixo risco”. |
| Registro `AvaliacaoSSVC` e migração 0023 | Guarda ocorrência, entradas, resultado, contexto, intervenção, evidências, autor e revisão em registros novos. Reavaliações não sobrescrevem as anteriores. |
| Remediação/mitigação explicitamente informada | Vincula a prioridade à intervenção e à implantação consideradas, em vez de atribuir uma decisão global à CVE. |
| Contexto com ativo, componente, ocorrência, CVE, CVSS, KEV, EPSS e versão da tabela | Permite conferir o que foi considerado. Não copia contatos, credenciais ou dados pessoais desnecessários. |
| Conferência do hash entre abertura e envio do formulário | Uma alteração de contexto durante o preenchimento exige recarregar; a decisão não é registrada sobre dados diferentes dos apresentados. |
| Revisão temporal e aviso de contexto alterado | Expiração ou mudança dos dados relevantes gera indicação de reavaliação, mantendo intacto o resultado histórico. |
| KEV não pode ser rebaixado para “sem evidência” | Exploração conhecida permanece evidência observada. EPSS não é convertido automaticamente em exploração ativa ou utilizado para desfazer KEV. |
| Respostas desconhecidas permanecem pendentes | Não se presume impacto pequeno, ausência de exploração ou controle de exposição. |
| Avaliação operacional bloqueada para ocorrência sugerida/corrigida ou ativo inativo/baixado | Evita classificar hipótese não confirmada ou apresentar nova urgência operacional para registro fora do escopo ativo. Histórico continua consultável. |
| Web e terminal usam o mesmo serviço | Evita regras e permissões divergentes entre interfaces. O terminal usa o MFA/reautenticação já existentes. |
| Leitura exige contexto autorizado; escrita exige alteração de incidências | Reutiliza permissões existentes: leitura de incidência, ativo e vulnerabilidade; escrita também exige `change_incidencia`. A política de MFA existente exige TOTP para contas com escrita. |
| Snapshot completo no evento de auditoria | Respostas, evidências, intervenção, autor e resultado também ficam representados no registro protegido pela cadeia de auditoria existente. |
| Links em incidências e ficha do ativo; última avaliação visível na lista | Integra SSVC à triagem que já existe. A coluna informa a última avaliação registrada e pede conferir sua validade; não representa prioridade atual automaticamente validada. |
| Correção de “Revisar status” na ficha do ativo | O link antigo abria uma rota exclusiva de POST. Agora abre o formulário de edição, com a autorização existente, e foi exercitado por teste. |
| Avaliações incluídas em exportação completa e backup | Preserva decisão e contexto em recuperação e entrega de dados. O backup anterior à migração também funciona. |

## Regras de uso

- Exploração é uma avaliação das evidências globais, não a afirmação de que o ativo local já foi comprometido.
- Exposição deve representar controles existentes e sustentados por evidência. Não basta dizer que o equipamento está na rede interna.
- Automação se refere à exploração automatizável; não é deduzida de uma nota CVSS.
- Impacto humano considera segurança das pessoas e missão. Não é copiado automaticamente da criticidade do ativo. O formulário liga à referência [Human Impact](https://certcc.github.io/SSVC/reference/decision_points/human_impact/).
- O campo de evidências deve justificar cada resposta e referenciar documentos, testes ou tickets. O texto é registrado, mas sua veracidade não é comprovada pelo software.
- A revisão padrão é em 30 dias e pode ser marcada entre amanhã e 90 dias. Essa é uma política local de revisão da avaliação; não é SLA oficial do SSVC nem prazo para uma ação “immediate”.
- Resultados pendentes não são recomendações de adiamento. Devem ter seu contexto completado.

A tradução de apresentação é: adiar com revisão, programar, antecipar manutenção e agir imediatamente. O código original da ação e a linha da tabela permanecem registrados.

## Funcionalidade, conectividade e objetividade

**Funcionalidade:** testes verificam as 72 combinações contra uma referência congelada, recusa de tabela incompleta/versão desconhecida, ausência de dados, adulteração do resultado enviado pelo cliente, KEV, contexto concorrente, expiração, diferentes implantações da mesma CVE, permissões, MFA, CSRF, escape de HTML, auditoria, exportação e restauração.

**Conectividade interna:** lista de incidências ou ficha do ativo → formulário → serviço transacional → registro e auditoria → histórico e última avaliação. O terminal percorre o mesmo serviço. GET não busca dados externos nem registra avaliações. O núcleo consulta o arquivo local de regras, não um serviço externo de decisão.

**Produção sintética:** com `DEBUG=0`, banco descartável e autenticação por senha/TOTP, foram exercitados formulário, POST, resultado, histórico e aviso de reavaliação após alterar o contexto. Status e SLA permaneceram iguais. Estáticos e verificador local de implantação também passaram. São requisições pela pilha Django; não substituem um navegador real, um proxy TLS real ou homologação da rede de produção.

**Objetividade:** avaliador puro com tabela explícita, serviço único e formulário Django. Nenhuma biblioteca, fila ou servidor adicional foi instalado. A quantidade de dados de uma tabela oficial não foi confundida com complexidade de código. Testes e migração permanecem separados das regras; não foram removidas validações para atingir uma contagem artificial de linhas.

## Atualização e acesso

1. Pare web/agendador e faça backup cifrado da instalação atual. Preserve `.env`, dados e chaves.
2. Extraia a distribuição completa em pasta nova e instale as dependências existentes.
3. Execute `python manage.py preparar_servidor`, aplicando **0023_avaliacoes_ssvc** e publicando estáticos.
4. Na web, abra “Incidências” → “SSVC”, ou o link SSVC na ficha do ativo.
5. No terminal, abra incidências → opção 5, “SSVC: consultar ou avaliar”.
6. Escolha a intervenção, responda ao contexto, registre evidências e marque a revisão. Consulte a explicação e o histórico depois do envio.

A avaliação não importa respostas de CISA Vulnrichment nesta fase e não possui mapeamento automático de EPSS para SSVC. Esses valores externos não substituem o julgamento local. O escopo implementado é uma tabela Deployer congelada, sem editor arbitrário de regras nem execução de código fornecido pelo operador.

## Evidências e limites

As evidências acompanham `docs/evidencias/fase2_ssvc/`: suíte completa, testes focados, verificações estáticas, teste de atualização, smoke em produção sintética e resumo da política com hash.

O teste de atualização utiliza schema 0022 descartável, gera backup antes da migração e confirma preservação dos dados depois da 0023. O teste de restauração preserva resultado e contexto de uma avaliação real criada pelo serviço.

A validade indicada combina os campos registrados e a data de revisão; mudanças fora do inventário ou declarações incorretas do operador não podem ser detectadas automaticamente. O snapshot do contexto é conservador: mudança em EPSS pode pedir revisão mesmo sem EPSS participar da tabela. A seleção dos níveis de impacto ainda exige analista qualificado.

Não foram executados PostgreSQL real, TLS de rede ou auditoria online atualizada de dependências nesta fase. SSVC não é uma probabilidade de ataque nem um modelo calibrado de perda financeira. A tabela é um exemplo de decisão do CERT/CC e precisa ser avaliada frente às responsabilidades e tolerância da organização; o Sauron não afirma certificação ou endosso.

Após exclusão de uma ocorrência, sua avaliação mantém código e contexto na base/exportação, com vínculo nulo; a interface desta fase é acessada pela ocorrência existente. Não foi criada uma área adicional de arquivo global.

Próxima fase: identidade de componentes, SBOM/VEX e deduplicação, mantendo a mesma disciplina de implementação, testes e relatório.
