# Sauron — Fase 3: identidade de componentes, SBOM e VEX

**Data:** 02/11/2026. **Base:** pacote completo da fase 2 (SSVC). **Migração:** 0024. Esta entrega inclui as fases anteriores e o código completo; o patch serve para revisão.

**Resultado verificado: 257 testes aprovados, sem falhas, em 94,990 segundos.** São 28 testes novos sobre os 229 anteriores. Ruff, Bandit, compatibilidade das dependências, migrações, configuração de produção e coleta de arquivos estáticos passaram. Evidências reproduzíveis estão em `docs/evidencias/fase3_componentes/`.

## O problema corrigido

Nome de software não é identidade suficiente para associar vulnerabilidades. Duas versões, empacotamentos ou ecossistemas podem compartilhar nomes, enquanto dois scanners podem descrever o mesmo componente. Duplicar incidências por arquivo importado aumenta ruído e pode inflar o risco; aceitar `not_affected` sem verificar autor e escopo pode ocultar um problema real.

A fase adiciona identidade PURL com versão exata, importação local de documentos, deduplicação por componente e rastreamento das fontes. Os novos achados se comunicam com o catálogo CVE, as incidências existentes, o contexto SSVC, a auditoria, o backup e a exportação. A aplicação continua exigindo decisão humana sobre aplicabilidade.

## Mudanças e motivos

| Mudança | Por que foi feita |
|---|---|
| PURL opcional em Software, normalizada por `packageurl-python==0.17.6` | Identificar pacote, ecossistema e versão usando uma implementação mantida, sem criar outro parser artesanal. |
| Unicidade de PURL por ativo; versões distintas podem coexistir | Evitar cópias do mesmo componente sem fundir versões diferentes. O cadastro legado sem PURL mantém a unicidade por ativo/nome/versão. |
| Identidade protegida quando já possui evidências ou incidências | Impedir que editar uma versão reatribua silenciosamente documentos e achados históricos. Uma nova versão deve ser outro registro. |
| Documento, itens SBOM, achados por componente e declarações VEX | Separar o que a fonte declarou, a identidade local e a decisão operacional. |
| Prévia sem gravação e importação atômica | Um componente inválido no fim do arquivo não deixa metade do inventário importada. |
| Fontes múltiplas e deduplicação de achados | Preservar origem, escopo e conteúdo sem multiplicar a mesma associação componente/CVE. |
| Reconciliação explícita com o catálogo local | Não inventar CVSS ou cadastrar CVE incompleta só para preencher um resultado. |
| Contexto SSVC inclui os novos indícios | Avisar que uma decisão precisa ser revista quando chegam evidências relevantes, mantendo o resultado histórico. |
| Web e terminal usam o mesmo serviço | Impedir diferenças de validação e autorização entre interfaces. |
| Novas tabelas e relações incluídas em backup/exportação | Conseguir restaurar o inventário sem perder a proveniência dos achados. |

A biblioteca de PURL é a única dependência de execução adicionada. Modelos, validação, serviço e apresentação têm responsabilidades separadas; não foram introduzidos outro framework, serviço remoto ou fila. A referência da biblioteca está no [repositório packageurl-python](https://github.com/package-url/packageurl-python).

## Fluxo e integração

1. O operador seleciona ativo, origem, escopo e arquivo JSON. A prévia valida o lote sem alterar o banco.
2. Ao gravar, o serviço valida novamente o conteúdo e as permissões. A gravação do documento, componentes e associações ocorre em uma transação.
3. Um componente com a mesma PURL exata no mesmo ativo reutiliza sua identidade; referências diferentes do documento continuam preservadas. Dados existentes não são sobrescritos pelo scanner. Conflito de versão ou CPE é rejeitado.
4. Um achado com CVE conhecida pode se vincular à incidência agregada ativo/CVE. Se ainda não existir incidência, nasce como **SUGERIDA**, para conferência. Uma incidência existente, inclusive corrigida, não é reaberta nem tem seu estado alterado.
5. Uma CVE ausente permanece como referência pendente. Após cadastrar a vulnerabilidade no catálogo, o operador pode reconciliar o documento. VEX importado antes do componente também pode ser reconciliado depois que a PURL existir no ativo.
6. SSVC passa a considerar as referências e documentos aplicáveis no contexto. Evidência nova torna a decisão anterior passível de reavaliação; não reescreve seu resultado, SLA ou aceite de risco.

A incidência operacional continua agregada por **ativo/CVE**. Os achados detalham os componentes que deram origem a ela; não geram várias parcelas de risco para o mesmo par. Antes de confirmar ou corrigir a incidência, o responsável precisa conferir todos os componentes relacionados. Software legado sem PURL não é fundido por semelhança de nome.

Dependências de pacote são guardadas como referências do documento SBOM. **Não criam dependências de rede ou caminhos de movimento lateral.** Confundir essas relações produziria um grafo enganoso.

## Formatos e limites reais

Foi implementado um **perfil local dos campos consumidos**, e não um validador universal dos padrões. Campos adicionais ficam no JSON arquivado, sem interpretação automática.

| Entrada | Perfil aceito |
|---|---|
| CycloneDX | JSON 1.5 ou 1.6; lista plana de 1 a 300 componentes de software; PURL e versão exatas; referências únicas; raiz opcional e dependências por `bom-ref`. |
| Tipos de componente | `application`, `framework`, `library`, `container` e `operating-system`. |
| Dependências | Referências conhecidas, sem autorreferência; até 2.000 arestas. Ciclos entre pacotes não são tratados como exploração ou propagação. |
| Vulnerabilidades da SBOM | CVE e associação explícita ao componente; até 500 pares referência/CVE; sem faixas adicionais de versão ou importação automática de notas CVSS. |
| OpenVEX | Contexto exato `https://openvex.dev/ns/v0.2.0`, autor declarado, timestamp com fuso e não futuro, revisão positiva e produtos com PURL exata. |
| Estados VEX | `affected`, `not_affected`, `fixed`, `under_investigation`; `affected` exige ação descrita; `not_affected` exige justificativa reconhecida ou declaração de impacto. |
| Tamanho | Até 2 MiB por arquivo; até 500 pares produto/CVE no VEX. |

Versões CycloneDX mais recentes, SPDX, CSAF, XML, arquivos compactados, serviços e componentes aninhados não são importados nesta fase. O importador rejeita perfis não suportados, referências ausentes, chaves JSON duplicadas e números não finitos. Não resolve URLs ou contextos JSON-LD pela rede. Consulte o formato completo na [referência CycloneDX 1.6](https://cyclonedx.org/docs/1.6/json/); este perfil cobre apenas parte dele.

Identificador/revisão de documento já importado para o ativo não pode reaparecer com conteúdo diferente. A repetição do mesmo JSON normalizado, ativo, tipo, origem e escopo reutiliza o documento. A mesma evidência recebida de outra origem ou com outro escopo mantém um registro próprio de proveniência.

## VEX e confiabilidade

VEX é declaração de aplicabilidade, e seu texto precisa de contexto. Os estados e justificativas usados se baseiam na [especificação OpenVEX](https://github.com/openvex/spec/blob/main/OPENVEX-SPEC.md).

Nesta implementação, **o autor informado não é autenticado e assinaturas não são verificadas**. `not_affected` e `fixed` nunca fecham incidências, reduzem risco ou mudam o VEX global do catálogo. `affected` pode gerar indício positivo para a PURL exata existente no ativo, sujeito ao mesmo fluxo SUGERIDA. Declarações contraditórias em documentos diferentes permanecem visíveis; duplicação ou contradição do mesmo produto/CVE dentro de um documento é rejeitada.

Uma importação não comprova instalação nem atualidade. Registros antigos não são apagados porque desapareceram da SBOM seguinte. A data de importação não equivale à data de observação do ambiente; timestamps de origem, quando fornecidos, permanecem no JSON. Reconciliação de implantação atual, atestação do emissor e expiração de evidências ficam como trabalho futuro.

## Controles de acesso e integridade

- Leitura de documentos exige as permissões de visualização de ativo, software, vulnerabilidade e incidência. Importar, fazer prévia ou reconciliar exige também cadastro de software e incidência. As rotas continuam sob autenticação e MFA da aplicação.
- O serviço relê a conta ativa e suas permissões atuais, evitando reutilizar permissões em cache. O terminal confere a autorização novamente depois da confirmação da prévia; perder a permissão enquanto se analisa o arquivo bloqueia a gravação. A mesma proteção foi aplicada ao registro SSVC no terminal.
- Gravações web usam POST e CSRF; downloads são protegidos. Valores externos são escapados nos templates. O upload tem limite de tamanho e o serviço não executa comandos ou busca recursos indicados pelo documento.
- O conteúdo fica como **texto JSON normalizado**, com ordenação determinística. O uso de texto evita que o banco reescreva números ou a ordem das chaves e altere a representação usada no hash. Não se preservam os bytes originais, espaços ou ordenação original.
- O SHA-256 é calculado sobre esse texto; o download recalcula e devolve HTTP 409 se houver divergência. Isso detecta diferença no conteúdo; não autentica a fonte e não protege contra alguém capaz de substituir simultaneamente conteúdo e hash.
- A auditoria registra operador, ativo, origem, escopo, resumo, revisão e hash. O corpo completo fica no documento, sem duplicar até 2 MiB a cada evento de auditoria.
- A tela limita a cinco as fontes recentes por achado. Todas as associações continuam no banco e na exportação. Componentes são paginados; os demais conjuntos têm os limites de importação descritos acima.

O novo módulo não concede administração de usuários a usuários comuns. A suíte completa mantém os testes de MFA e bloqueio administrativo das fases anteriores; esta fase não substitui a política de acesso já implementada.

## O que foi testado

Os 28 testes novos cobrem normalização PURL, versões, estrutura de documentos, falhas sem gravação parcial, idempotência, fontes distintas, pendência no catálogo, conflitos de revisão, VEX sem supressão, declarações contraditórias, identidade imutável, contexto SSVC, autorização web/terminal, revogação durante confirmação, CSRF, escape de HTML, download íntegro e adulterado, backup/restauração das novas relações e exportação. Também conferem que dependências SBOM não criam rede, que incidências corrigidas não reabrem e que a limitação visual de fontes não perde dados.

| Verificação | Resultado |
|---|---|
| Suíte Django completa | 257 testes, 94,990 s, OK. Erros simulados de serviços externos/MFA no log são cenários deliberados de teste. |
| Ruff | Sem ocorrências. |
| Bandit, código de execução exceto migrações | Sem ocorrências ou erros de análise. Não é prova de ausência de vulnerabilidades. |
| `pip check` | Dependências compatíveis. Não equivale a auditoria de CVEs. |
| `makemigrations --check --dry-run` | Nenhuma alteração de modelo sem migração. |
| Check Django de produção e `collectstatic` | Aprovados com a configuração de verificação. |
| Atualização 0023 → 0024 | Banco SQLite descartável: dados legados preservados, backup cifrado antes da migração e PURL antiga permanece vazia. |
| Fluxo com `DEBUG=0` | Cliente de teste: HTTPS simulado, login/TOTP, EPSS simulado, SSVC, upload SBOM/VEX, achados, download, cookies e estáticos verificados. |

O backup completo foi restaurado com documentos, declarações e associações de fontes. A compatibilidade do backup antes da migração 0024 também foi exercitada.

**Limites da validação:** não houve execução contra PostgreSQL real, TLS real, SMTP real ou infraestrutura externa de produção. O cenário EPSS usa resposta simulada. A auditoria online de vulnerabilidades das dependências não foi concluída por indisponibilidade de DNS no ambiente; Bandit e `pip check` não a substituem. Não se afirma certificação de padrões, verificação de assinatura, resistência a carga de produção ou ausência total de falhas.

## Como atualizar e usar

1. Pare os serviços e gere um backup cifrado com a versão instalada. Preserve banco, configurações e chaves em local protegido.
2. Extraia o pacote completo em uma pasta nova e siga o guia de atualização do seu sistema operacional. Não sobrescreva suas configurações com exemplos.
3. No ambiente virtual da aplicação, execute `python -m pip install -r requirements.txt`. A dependência PURL é nova e precisa ser instalada antes de iniciar os comandos Django.
4. Execute `python manage.py preparar_servidor` para aplicar a migração 0024 e preparar os estáticos. Revise a configuração usando `python manage.py verificar_implantacao --json` antes de retomar a operação.
5. Na web, entre em **Software → SBOM/VEX**, selecione ativo, escopo e origem, envie o arquivo para prévia e confira o resultado. Para gravar após a prévia, selecione novamente o arquivo e marque a opção de gravação. No terminal, use a opção **8** do menu operacional.
6. No detalhe do documento, confira componentes, referências, fontes e declarações. Use **Reconciliar achados com o catálogo atual** após cadastrar CVEs pendentes ou componentes que faltavam. O link SSVC abre a ocorrência agregada.

Os arquivos `docs/exemplos/exemplo-sbom-cyclonedx.json` e `docs/exemplos/exemplo-openvex.json` são exemplos **sintéticos para homologação**, não evidências do seu ambiente. Importe-os apenas em um ativo de teste. A CVE ilustrativa só se vincula operacionalmente se já estiver no catálogo local; o exemplo VEX declara investigação, sem afirmar ausência de risco.

## Avaliação crítica e próxima fase

O inventário agora consegue explicar de onde veio uma associação componente/CVE. Ainda depende da qualidade e atualidade das fontes. Um arquivo bem formado com um hash consistente pode conter informação falsa. Sem validação de instalação, confiança no emissor e ciclo de vida das evidências, um painel visualmente completo pode continuar desatualizado.

A próxima fase proposta é um **grafo com relações tipadas de rede, identidade e negócio**, separando alcance técnico, privilégio exigido e dependência operacional. Só depois faz sentido ampliar as operações do modo Euler para analisar caminhos, pontos de corte e cenários. Dependência de biblioteca, tráfego permitido e possibilidade de exploração não devem receber o mesmo significado matemático.
