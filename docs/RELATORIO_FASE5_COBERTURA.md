# Sauron — Fase 5: qualidade e cobertura das evidências

**Data:** 02/11/2026. **Base:** pacote completo da fase 4. **Migração:** `0026_cobertura_evidencias`. Nenhuma biblioteca de execução foi adicionada nesta fase.

**Validação final: 325 testes aprovados, sem falhas, em 124,342 segundos.** São 35 testes novos sobre os 290 da fase anterior. Ruff, Bandit, dependências compatíveis, migrações e configuração de produção passaram nas verificações descritas abaixo.

## Resultado e problema resolvido

Um grafo vazio não explica se houve uma revisão sem relações identificadas ou se ninguém coletou os dados. Contar ativos com vínculos também não informa quantos foram revisados. A fase acrescenta um perímetro explícito, revisões históricas e indicadores separados para essas situações, com interfaces web, API e terminal.

O resultado continua sendo **cobertura declarada do inventário**. Não comprova completude da descoberta, veracidade das fontes, ausência de acesso real ou segurança do ambiente. Não há nota composta, probabilidade de ataque ou redução automática de risco por preencher um formulário.

## O que foi feito e por quê

| Alteração | Motivo |
|---|---|
| `PerimetroRelacoes` com nome/descrição e `MembroPerimetro` com vínculos aos ativos | Dar um denominador explícito ao escopo, sem presumir que todo ativo da organização pertença a toda aplicação. |
| Nome do perímetro imutável e edição com controle de versão | O nome corresponde ao escopo das relações. Renomear ou sobrescrever uma edição concorrente poderia mudar silenciosamente seu significado. |
| `RevisaoCobertura` como registro histórico | Preservar quem revisou, quando, o que declarou e quais limitações registrou. Uma nova avaliação acrescenta outro registro. |
| Resultados “relações revisadas”, “nenhuma relação identificada” e “lacunas” | Distinguir revisão completa declarada, ausência declarada e incerteza. |
| Contexto vinculado por SHA-256 | Retirar uma revisão do numerador quando os dados pertinentes mudarem. O hash não é assinatura ou autenticação do emissor. |
| Elegibilidade compartilhada entre grafo e qualidade | Evitar que a tela de qualidade considere válido um vínculo que o grafo exclui. |
| Motivos de exclusão e filtros por estado | Permitir tratar pendências concretas, em vez de apresentar apenas um percentual. |
| Integração com SSVC, auditoria, backup e exportação | Preservar histórico e tornar mudanças de contexto visíveis sem alterar decisões operacionais. |

São três tabelas novas; a relação muitos-para-muitos usa a tabela explícita de membros. Não há serviço externo, coletor, fila ou framework novo.

## Perímetro e efeito nos grafos existentes

O perímetro lista os ativos que o operador declara pertencerem ao escopo. Ativos inativos/baixados podem permanecer como membros históricos, mas não entram no denominador operacional. Referências aos ativos usam proteção contra exclusão em cascata.

**Definir um perímetro afeta o grafo do escopo de mesmo nome:** os nós passam a ser apenas seus membros operacionais. Relações com endpoints fora dele continuam no banco e aparecem como pendências; não são apagadas ou corrigidas automaticamente.

Escopos legados sem perímetro continuam usando os ativos operacionais de todo o inventário, como na fase 4, agora com aviso explícito. A migração não infere membros, não cria revisões e não atribui cobertura automaticamente. Somente aplicar a migração preserva o comportamento desses grafos; declarar um perímetro é uma ação posterior e consciente.

A inclusão de um ativo sem vínculos pertinentes não invalida desnecessariamente a revisão de outro ativo. Quando a alteração torna elegível uma relação antes fora do perímetro, a revisão do ativo afetado passa a indicar contexto alterado. Mudar a descrição/definição do perímetro também invalida as revisões vinculadas.

## Revisões e condições para registro

Cada revisão especifica perímetro, ativo operacional membro, camada e, na camada IDENTIDADE, principal exato. Os registros de camadas e identidades diferentes permanecem separados, inclusive quando não há vínculos cadastrados.

| Resultado declarado | Regra aplicada |
|---|---|
| `REVISADO` | Pelo menos uma relação elegível incidente ao ativo e nenhuma relação vigente pendente. |
| `SEM_RELACOES` | Nenhuma relação vigente incidente no recorte. Vínculos vigentes vencidos ou fora do perímetro impedem essa declaração. Registros revogados permanecem históricos e não a impedem. |
| `LACUNAS` | Registro explícito de incerteza, coleta incompleta ou pendências. Não entra no numerador de revisões completas. |

Em todos os casos, são obrigatórias evidência/limitações e datas. A observação não pode estar no futuro, e a revisão deve ocorrer depois dela. A validade máxima é **90 dias após a observação**, como política administrativa local desta fase; esse prazo não vem de CVSS, EPSS ou de uma exigência atribuída ao NIST. É possível registrar uma avaliação histórica já vencida, que não contará como atual.

Antes de gravar, a aplicação recalcula o contexto e compara com a prévia. Mudança pertinente durante o preenchimento exige recarregar. Alterar a seleção de ativo/camada/principal também exige nova prévia.

Uma revisão salva não pode ser editada pelo fluxo da aplicação. A última revisão é a de maior ID de registro para o mesmo ativo/perímetro/camada/principal. Ela substitui a anterior na análise atual, mesmo que declare lacunas ou já esteja vencida; não se procura uma avaliação antiga mais favorável. O histórico anterior continua consultável.

## Indicadores e operações matemáticas

Para o recorte selecionado, considere:

- **N:** membros operacionais do perímetro.
- **R:** ativos cuja última revisão declara `REVISADO` ou `SEM_RELACOES`, está no prazo e conserva o contexto.
- **V:** ativos com pelo menos uma relação elegível incidente, independentemente de revisão.

As medidas são **cobertura declarada = 100 × R/N** e **representação por vínculos = 100 × V/N**, com duas casas decimais. Se N for zero, a API retorna `null` e a tela informa que o percentual não pode ser calculado. Perímetro vazio não vira 100% revisado.

Um ativo com dez relações pode aumentar V e continuar fora de R por não ter revisão. Um ativo sem vínculos pode entrar em R após uma declaração de ausência com evidência e contexto preservado. Nenhum dos dois casos comprova segurança real.

Os estados atuais são mutuamente exclusivos: sem revisão; contexto alterado; revisão vencida; lacunas; revisado; sem relações. Se contexto e prazo tiverem mudado, “contexto alterado” tem precedência. Contagens do painel sempre usam o perímetro completo; filtros e limite de exibição não mudam o denominador.

A análise das relações também usa motivos exclusivos, em ordem: revogada; observação futura; revisão vencida; endpoint inativo/baixado; endpoint fora do perímetro; elegível. Uma linha com vários problemas conta no primeiro motivo aplicável. Contagens de relações e de ativos não devem ser somadas como se tivessem o mesmo denominador.

O processamento distribui cada relação aos seus endpoints uma vez e calcula os resumos por ativo, evitando varrer todas as relações novamente para cada membro. A última revisão é selecionada com função de janela no banco e índice por perímetro/camada/principal/ativo/ID. A [documentação Django de expressões e janelas](https://docs.djangoproject.com/en/5.2/ref/models/expressions/#window-functions) descreve o recurso utilizado. Isso não representa ensaio de carga de produção.

## Contexto, integridade e SSVC

O hash de uma revisão considera identificação e definição do perímetro, ativo e estado, camada/principal e relações incidentes, incluindo metadados e motivo atual de elegibilidade. Não é recalculado com um timestamp diferente a cada consulta: mudar de dia sem cruzar um prazo não invalida a revisão. Vencimento de relação ou mudança relevante altera o contexto.

O histórico guarda hash, contagens e declaração do operador; não duplica uma cópia completa do grafo em cada avaliação. O hash sozinho não permite reconstruir os dados anteriores nem os autentica. Auditoria e backups continuam necessários para preservar evidências e versões.

O contexto SSVC recebe somente um hash de membros/perímetros e últimas revisões, sem expor o texto da evidência ou o principal a quem só pode ler SSVC. Registro novo, vencimento ou edição do perímetro podem pedir reavaliação. Edições de perímetro invalidam o contexto SSVC de forma conservadora, mesmo quando a revisão específica de um ativo não foi afetada por um membro sem vínculos.

Ativos sem perímetro/revisão novos mantêm a estrutura anterior do contexto SSVC. Resultados históricos, aceite de risco, SLA, notas de vulnerabilidade e estados de incidência não são reescritos pelo módulo de qualidade.

## Segurança e papéis

Consultar o módulo exige leitura de ativo, relação, perímetro e revisão. Cadastro/edição de perímetro exige sua permissão específica; registrar revisão exige `add_revisaocobertura`. O serviço relê conta ativa e permissões na transação de gravação, incluindo depois de confirmações no terminal. Edições de membros são auditadas com IDs adicionados/retirados, autor e total.

Os grupos oficiais passam a ter:

| Grupo | Qualidade e histórico | Registrar revisão | Administrar perímetro |
|---|---|---|---|
| Auditores | Sim | Não | Não |
| Operadores | Sim | Sim | Não |
| Gerentes | Sim | Sim | Sim |

Não há permissões padrão nem rotas para editar/excluir uma revisão histórica. As novas permissões de escrita exigem TOTP pela política existente, inclusive em contas sem staff. Um revisor comum continua bloqueado na administração de usuários/grupos e na edição de perímetros sem autorização.

Gravações web exigem POST e CSRF; a API de consulta aceita GET sem modificar cadastros. Textos são escapados na apresentação. Não são buscadas URLs fornecidas em evidências e não há varredura de rede. Os campos não devem receber senhas, tokens ou segredos.

## Limites e verificação

O recorte conserva os limites da fase 4: até 10.000 ativos operacionais e 50.000 relações. O serviço de perímetro aceita até 10.000 membros por edição e rejeita IDs inexistentes ou repetidos. O painel exibe de 1 a 100 ativos por consulta, padrão 50, permitindo filtrar o estado. Uma revisão aceita até 4.000 caracteres de evidência; a descrição do perímetro aceita até 1.000.

Os 35 testes novos cobrem denominadores vazios, motivos, validade, alteração de definição, isolamento de identidades/camadas, revisão de ausência versus coleta ausente, pendências, última avaliação, imutabilidade, edição concorrente, proteção de membros, autorização e revogação, revisor sem administração, MFA, CSRF, fluxos web/API/terminal, escape de HTML, ausência de rede, auditoria, SSVC, backup e exportação.

| Verificação | Resultado |
|---|---|
| Suíte completa | Resultado exato no início do relatório e em `TESTES.txt`. Inclui os 290 testes anteriores. |
| Ruff e Bandit | Sem ocorrências nas verificações executadas. Não provam ausência de vulnerabilidades. |
| `pip check` | Dependências compatíveis; não equivale a auditoria de CVEs. |
| Migrações, check de produção e estáticos | Aprovados; nenhuma mudança de modelo sem migração. |
| Atualização 0025 → 0026 | Banco SQLite descartável: ativos, relação tipada, PURL, SBOM e CVE preservados; nenhum perímetro/revisão inferido. |
| Backup anterior à migração | Backup cifrado com tabelas novas ausentes restaurado no schema atual, com auditoria validada. |
| Backup atual | Membros e revisões restaurados com suas relações; exportação completa inclui as três coleções novas. |
| Fluxo com `DEBUG=0` | Perímetro com CSRF validado; membros SQL; grafo restrito; prévia, revisão, detalhe e API. No cenário sintético, 1 de 2 ativos revisados resulta em 50%; nova evidência retira a revisão do numerador e preserva o histórico. |

Evidências estão em `docs/evidencias/fase5_cobertura/`. Avisos de falha de e-mail e HTTP 503 no log da suíte são cenários simulados deliberadamente.

Não houve homologação em PostgreSQL real, SMTP real, TLS real, AD/Entra/LDAP ou infraestrutura externa. HTTPS é simulado pelo cliente Django. Concorrência e dimensionamento precisam de validação no banco/ambiente real. A auditoria online de vulnerabilidades das dependências continua pendente pela indisponibilidade de DNS do ambiente; as análises locais não a substituem.

## Referências e julgamento crítico

O [NIST SP 800-137](https://csrc.nist.gov/pubs/sp/800/137/final) trata monitoramento contínuo como apoio à visibilidade de ativos e à avaliação dos controles. Foi usado como orientação para tornar revisão e atualidade explícitas. As fórmulas desta fase são definições locais do Sauron, não índices padronizados nem atestado de conformidade.

O [repositório OWASP Dependency-Track](https://github.com/DependencyTrack/dependency-track) foi consultado como referência de plataforma que usa inventários SBOM para apoiar análise de risco da cadeia de software. Não foram importados seu código, seus serviços ou uma suposta métrica de confiança; esta fase trata a qualidade das declarações do próprio inventário Sauron.

O ponto mais fraco permanece humano e operacional: é possível cadastrar uma evidência falsa ou definir um perímetro estreito e obter um percentual elevado. Auditoria, definição explícita e contagens ajudam a tornar isso examinável; não descobrem os ativos que ninguém cadastrou e não fazem uma revisão independente. Aumentar o percentual não deve virar uma meta dissociada da abrangência do perímetro.

Identidades como nós próprios, grupos/delegações, pré-condições de exploração e confiança verificável no coletor continuam para fases seguintes. Não se introduziu corte mínimo de “ataque” antes de modelar o que cada caminho e remoção realmente representam.

## Atualização e uso

1. Pare serviços, faça backup cifrado na versão instalada e preserve configurações, banco e chaves.
2. Extraia o pacote completo em pasta nova. No ambiente virtual, mantenha a base com `python -m pip install -r requirements.txt`.
3. Execute `python manage.py preparar_servidor` para aplicar 0026, preparar estáticos e atualizar grupos oficiais. **Operadores passam a poder registrar revisões.** O comando reaplica a política oficial; confira personalizações anteriores e conceda as novas permissões explicitamente em papéis próprios.
4. Revise a implantação com `python manage.py verificar_implantacao --json`.
5. Abra **Relações por camada → Qualidade, cobertura e revisões**, ou o acesso no Modo Euler. Declare perímetro com nome exato do escopo e membros conscientes de que isso limita seu grafo.
6. Consulte camada/principal, abra “Registrar nova revisão” no ativo escolhido, confira o contexto, registre evidência/limitações e prazo. Para outro recorte, volte ao painel e abra outra prévia.
7. No terminal: menu operacional **9 → 5**, com opções de consulta, declaração/edição de perímetro e revisão de ativo.

API de consulta: `/api/qualidade-relacoes/?perimetro=ID&tipo=REDE`. IDENTIDADE exige `principal`; opcionais: `limite` e `filtro` (estado). A API usa sessão autenticada, MFA e as mesmas permissões da web. Não retorna porcentagem de segurança.

O roteiro `docs/exemplos/roteiro-cobertura-evidencias.md` permite conferir os resultados em homologação sem usar dados reais.
