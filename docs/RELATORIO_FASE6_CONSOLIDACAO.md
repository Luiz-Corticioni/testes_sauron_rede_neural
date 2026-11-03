# Fase 6 — Acesso, cenários de 30 dias e orientação de uso

**Data:** 03/11/2026. **Base:** pacote completo da fase 5, migração 0026.

**Validação final: 349 testes aprovados, sem falhas, em 136,107 segundos.** Foram acrescentados 24 testes de regressão e atualizados os testes do contrato financeiro. As evidências estão em [evidencias/fase6_consolidacao](evidencias/fase6_consolidacao).

## Resultado e julgamento técnico

Esta entrega reduz três problemas concretos: autorizações antigas podiam sobreviver na memória da sessão de terminal; a conversão de EPSS em probabilidade anual sugeria precisão sem sustentação; e várias análises exigiam conhecimento técnico sem explicar o que fazer com o resultado. O pacote contém a aplicação completa e as fases anteriores.

O Sauron ainda não deve ser apresentado como motor de previsão de perdas ou ataques. É um inventário com evidências, gestão de ocorrências e laboratórios de análise. Sua utilidade depende de cobertura, atualidade e confirmação dos dados. Mais gráficos não compensam um inventário incompleto. Esta fase melhora a interpretação dos resultados; não certifica o ambiente real de produção.

## 1. Autorização atual e MFA

**Problema:** o cache de permissões do objeto User podia continuar concedendo acesso depois de uma revogação, especialmente em sessões CLI longas. Validar apenas ao abrir o menu também deixava uma janela durante preenchimento, confirmação ou consulta externa.

**Mudança:** `aplicacao/autorizacao.py` consulta novamente a conta ativa e suas permissões. Serviços compartilhados de cadastro, decisões, SSVC, documentos, relações, cobertura, CSV e operação passam pela mesma regra. Escritas revalidam depois da obtenção da trava, antes da alteração. A segunda aprovação usa a conta atual do aprovador. Aceitar risco exige sua permissão específica mesmo quando a decisão já foi preparada pelo formulário.

O contexto CLI revalida sessão, dispositivo e reautenticação nas escritas; se expirarem durante o preenchimento, a operação falha sem abrir um prompt dentro da transação. O operador volta ao menu, autentica-se e refaz a ação. Exportações e execução de rotinas também revalidam depois de perguntas demoradas. A criação administrativa no terminal usa os validadores de senha do Django e reconfere privilégios antes de criar a conta.

A política vigente permanece: todas as sessões passam por MFA; contas privilegiadas usam TOTP. A fase não concede administração de usuários a operadores comuns. Os testes cobrem revogação direta/de grupo, conta desativada, cache positivo e negativo, edição/exclusão negadas, segunda aprovação e dispositivo revogado. A suíte anterior continua verificando separação de papéis, MFA, replay, sessões e rotas administrativas.

No navegador, a expiração da reautenticação durante um cálculo retornava HTML de MFA, que virava a mensagem inútil “servidor respondeu 200”. O cliente HTTP agora identifica esse retorno e a tela financeira oferece **Confirmar MFA**. Resultados antigos são limpos quando parâmetros mudam ou a solicitação falha.

**Limite:** isto fecha a reutilização de permissões antigas nos fluxos tratados; não promete revogação instantânea entre quaisquer duas instruções concorrentes em todos os bancos. Homologação de concorrência com PostgreSQL continua pendente.

## 2. Horizonte financeiro de 30 dias

**Problema:** anualizar EPSS e desenhar evolução mensal dava aparência de previsão. EPSS descreve a probabilidade de exploração de uma CVE no mundo real nos próximos 30 dias, e não a chance de perda financeira de um ativo específico. [Definição oficial da FIRST](https://www.first.org/epss/).

**Mudança:** serviço, matemática, API, terminal, gráficos e textos usam **30 dias**. Foram retirados anualização, piso numérico de KEV, probabilidade inventada a partir de CVSS e curvas mensais/diárias. KEV continua como evidência de exploração e priorização. CVSS participa apenas da hipótese de impacto, explicitada na tela.

O laboratório mostra média, mediana, P5/P90/P95/P99, frequência de perda não nula, excedência e comparação após correções hipotéticas. Usa amostras comuns para comparações reproduzíveis. No mesmo ativo considera a maior perda sorteada; soma perdas entre ativos. O teto vale para os mesmos 30 dias. Contribuições atribuídas e ganhos marginais têm significados distintos; ganhos individuais não devem ser somados.

Custos padrão são exemplos didáticos. Os fatores de cenário interno/internet começam em **1**, evitando atribuir redução arbitrária aos ativos internos. Qualquer ajuste é hipótese do operador, não eficácia de controle comprovada. Independência entre vínculos, no máximo um evento por vínculo e máximo por ativo são simplificações declaradas. O módulo **não implementa FAIR completo** e não oferece intervalo de confiança sobre perdas reais. P95 é percentil dos cenários gerados.

### Dados insuficientes não são perda zero

Todos os vínculos elegíveis precisam de EPSS com observação de origem coerente, valor/CVE/data correspondentes e atualização na janela local de até dois dias. Essa janela é política do Sauron, não garantia da FIRST. Sem esses dados, retorna `disponivel=false`, lista pendências e não produz estimativas parciais silenciosas. Inventário sem vínculos elegíveis produz cenário vazio com zero, identificado pelo escopo. EPSS observado igual a zero é dado válido.

Aceitas e mitigadas permanecem no cenário: aceitar risco ou declarar mitigação não equivale a comprovar correção. Corrigidas, sugeridas e ativos baixados/inativos ficam fora. O cache inclui versão do modelo, versão dos dados, parâmetros e data para respeitar o envelhecimento do EPSS. O limite continua em oito milhões de vínculos × cenários por requisição.

### Alteração intencional do contrato

| Contrato anterior | Contrato atual |
| --- | --- |
| `ALE`, `ganho_ALE`, `ALE_atribuida` | `media`, `ganho_media`, `media_atribuida` |
| `probabilidade_anual` | `probabilidade_cenario_30d` |
| Séries mensais/diárias | Distribuição e excedência em 30 dias |
| Parâmetro `piso_kev` | Removido; envio retorna HTTP 400 |
| Resultado sem horizonte explícito | `versao_modelo=sauron.montecarlo/30d-v1`, `horizonte_dias=30`, `disponivel` |

Integrações externas devem atualizar seus leitores; não há aliases anuais que escondam mudança de unidade. Sem dados suficientes, `antes` e `depois` são nulos. O cliente deve conferir `disponivel` antes de ler estatísticas. A interface e a CLI incluídas já usam o contrato novo.

## 3. Atualização EPSS acessível ao operador

O botão **Atualizar EPSS** consulta a FIRST mediante POST explícito, com CSRF, MFA/reautenticação e permissões de leitura dos dados necessários e alteração de vulnerabilidades. Revalida autorização depois da consulta de rede e antes da gravação. GET não consulta a fonte externa.

Na web, cada ação consulta no máximo 50 CVEs, priorizando ausentes ou antigas; informa contagens e avisos. Catálogos maiores devem usar sincronização operacional completa. Na CLI, a opção 8 do menu CVE pede confirmação da consulta externa e chama o mesmo serviço. O comando `python manage.py sync_epss` permanece disponível para a rotina completa. Registros preservam proveniência e autoria. Falha de rede não fabrica ou apaga EPSS.

## 4. Orientação para stakeholders

Foram acrescentadas ajudas recolhíveis com **objetivo, exemplo, interpretação e próximo passo** em nove tarefas: visão geral, incidências, SSVC, SBOM/VEX, grafo por camada, qualidade de relações, revisão de cobertura, laboratório financeiro e Modo Euler. A ajuda fica próxima da tarefa, com acesso ao guia.

O guia rápido inclui roteiros para responsável pelo negócio, analista de segurança e mantenedor do inventário, respeitando permissões nos acessos oferecidos. O glossário explica SSVC, PURL/SBOM, VEX, cobertura, média, mediana e P95. Painéis de cobertura exibem rótulos em português; chaves de máquina da API foram preservadas, com rótulos adicionais.

Exemplo financeiro: média de R$ 10 mil antes e R$ 7 mil depois representa redução **modelada** de R$ 3 mil em 30 dias, sem comprovar economia realizada. O resumo destaca média, mediana e P95; explica por que mediana zero pode coexistir com perdas elevadas. Gráficos têm tabelas equivalentes para leitura acessível. Isso facilita o entendimento, mas não substitui pesquisa de usabilidade com usuários reais ou auditoria completa de acessibilidade.

## 5. Dependências e CI

As Actions existentes foram fixadas em commits consultados na API oficial do GitHub: checkout, setup-python, upload-artifact e Trivy. A referência anterior do Trivy não existia sem o prefixo `v`; foi resolvida a tag `v0.28.0` e fixado seu commit. Dependabot permanece propondo atualizações. Pinning impede movimentação silenciosa de tags; não audita conteúdo do fornecedor.

`pip-audit` consultou o PyPI para as oito dependências de `requirements.txt`, sem instalar pacotes: **nenhuma vulnerabilidade conhecida encontrada**. Usou `--no-deps --disable-pip`: não foi auditoria integral de transitivas, ferramentas de desenvolvimento, sistema operacional ou imagem. Versões e dependências da aplicação não foram alteradas nesta fase. O workflow completo do GitHub Actions não foi executado neste computador.

## 6. O que foi efetivamente verificado

| Verificação | Resultado e alcance |
| --- | --- |
| Suíte Django | 349 testes aprovados; 24 novos, além de ajustes dos testes financeiros anteriores |
| Ruff | Sem erros |
| JavaScript | Sintaxe dos arquivos alterados e cinco cenários do cliente HTTP aprovados: JSON, MFA expirado, login expirado, erro JSON e erro HTML |
| Bandit | Sem achados e sem erros no escopo inventario/sauron_web, excluídas migrações |
| `pip check` | Dependências instaladas compatíveis |
| Migrações | `makemigrations --check --dry-run`: nenhuma alteração; esquema continua em 0026 |
| Configuração de produção | `check --deploy --fail-level WARNING` com segredos/configuração sintéticos: aprovado |
| Estáticos | `collectstatic` e atendimento via WhiteNoise com `DEBUG=0`: aprovados |
| Integração `DEBUG=0` | Senha/TOTP, CSRF, EPSS simulado → banco → telas; SSVC; SBOM/VEX; relações/grafo/cobertura; API financeira de 30 dias; expiração MFA: aprovados |
| Navegador real | Base sintética em loopback, login/TOTP, interface financeira, comparação e ajuda; detalhes em BROWSER.txt |
| Distribuição | ZIP completo com CRC e manifesto SHA-256 por arquivo; sem banco, segredos, sessões ou ambiente virtual |

O primeiro teste completo identificou uma fixture antiga que mantinha uma segunda vulnerabilidade sem CVE/EPSS no cenário financeiro. Foi corrigido o recorte do teste, acrescentando verificações explícitas de indisponibilidade antes da sincronização e disponibilidade depois; a regra de produção não foi relaxada para fazê-lo passar.

## 7. Atualização e próximos passos

Faça backup do banco e dos segredos pelos procedimentos documentados. Substitua o código pelo pacote completo, preserve a configuração privada, execute `python manage.py preparar_servidor` e reinicie web e agendador. Não há nova migração de esquema nem nova dependência; a preparação atualiza estáticos e grupos oficiais. Atualize consumidores externos da API financeira. O pacote não inclui credenciais de homologação ou bases de demonstração.

Continuam pendentes: homologação nativa com PostgreSQL/driver, TLS/proxy reais, entrega SMTP real, recuperação em ambiente separado e execução do CI nas plataformas de destino. O HTTPS do cliente Django exercita regras/cabeçalhos; não testa conexão TLS real. A coleta FIRST no teste integrado foi simulada: a auditoria PyPI on-line não certifica disponibilidade de CVE/EPSS no servidor final.

**Docker foi adiado expressamente pelo usuário.** Não foram alterados Dockerfile/Compose nem realizada implantação ou validação de imagem nesta fase. O pin da Action preserva o pipeline existente e não equivale a executá-lo. A próxima etapa pode ensinar construção, segredos/volumes, inicialização, saúde, backup e atualização com Docker, com testes práticos.

Após homologação operacional, priorize conectores com origem/validade, medidas de qualidade dos dados e calibração das hipóteses com observações reais. Novos modelos matemáticos agregam valor quando a equipe consegue explicar entradas, limitações e decisões resultantes.
