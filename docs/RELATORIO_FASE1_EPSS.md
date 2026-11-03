# Fase 1 — EPSS, proveniência e triagem objetiva

## Entrega

A primeira fase implementa histórico e proveniência do EPSS, percentil, integridade do vínculo com a CVE, apresentação na triagem e ligação ao Monte Carlo. Preserva os controles de autenticação e autorização da entrega etapa 2. SSVC, SBOM/VEX, grafo ampliado e novas operações Euler continuam nas fases seguintes; não foram apresentados como implementados.

**Validação final: 210 testes, zero falhas, em 71,967 segundos.** Foram acrescentados 16 testes aos 194 anteriores. Ruff, Bandit, compatibilidade de dependências, verificação de migrações, check Django de produção e coleta de estáticos passaram.

## Mudanças e razões

| Mudança | Por que foi feita |
|---|---|
| Modelo `ObservacaoEPSS` e migração 0022 | Preserva CVE, data, probabilidade, percentil, modelo quando informado, fonte, primeira coleta e assinatura SHA-256 do conteúdo normalizado. |
| Histórico com unicidade por CVE/data/assinatura | Importar de novo a mesma observação não duplica o histórico; uma correção da fonte no mesmo dia pode ser registrada sem apagar a anterior. |
| Ponteiro da vulnerabilidade para a observação corrente | Mantém compatibilidade com os campos EPSS existentes e permite identificar a evidência usada. Evita consultar um histórico inteiro para montar cada linha da lista. |
| Serviço EPSS separado do Monte Carlo | Enriquecimento é uma responsabilidade de inventário, não do simulador financeiro. O caminho antigo continua importável, apontando para a única implementação. |
| Probabilidade, percentil e datas validados antes de gravar | Recusa NaN, infinito, booleanos, intervalos inválidos, datas futuras e duplicação da mesma CVE na resposta. Lote inválido não grava parcialmente. |
| Consulta em lotes de 50 e limite de caracteres | Compatível com o limite documentado de 2000 caracteres do parâmetro CVE da FIRST e com identificadores locais de até 30 caracteres. |
| Transação somente depois da rede | Não mantém o banco travado enquanto espera a fonte externa. Reconsulta e trava o cadastro para lidar com mudança durante a coleta. |
| Dados históricos não substituem referência mais recente | Uma resposta antiga entra no histórico, preservando o valor corrente. |
| Falhas e CVEs ausentes geram avisos sem zerar valores | Ausência de dado não vira 0% nem sinal de segurança. O comando termina com erro quando a sincronização é incompleta. |
| Limpeza do EPSS ao trocar a CVE de um cadastro | Impede atribuir a uma CVE nova a inteligência da antiga. O histórico da CVE anterior permanece preservado. |
| Validação da relação entre valor, data, CVE e evidência | Impede salvar um valor divergente apontando para uma observação de origem que não o sustenta. |
| Campos EPSS somente leitura no admin | Não permite editar manualmente o valor e manter uma falsa aparência de informação da FIRST. |
| Lista de vulnerabilidades com EPSS, percentil e estado de atualização | Integra os dados à triagem existente, sem criar outro painel com a mesma finalidade. Probabilidade e percentil aparecem separados; valores positivos muito pequenos aparecem como <0,01%, preservando a distinção em relação a zero. |
| Filtros de dados ausentes, atualizados, desatualizados e sem origem; ordenação por EPSS | Permite procurar lacunas e ordenar pelo critério escolhido. Não cria um score composto arbitrário. |
| Página de histórico paginada | Mostra evidências com a permissão já existente `view_vulnerabilidade`, sem nova camada de papéis. GET não acessa a internet nem altera o inventário. |
| Evidência EPSS nas saídas do Monte Carlo e versão nova de cache | Identifica a observação e a fonte utilizadas, expõe o estado de atualização e evita servir o formato antigo de cache. |
| Histórico incluído na exportação completa e no backup | Evita perder a origem dos resultados ao exportar ou restaurar. A exportação JSON legada conserva seu contrato anterior. |
| Backup compatível com banco anterior à 0022 | Permite fazer backup antes de aplicar o novo campo/tabela. Foi validado sobre um schema 0021 descartável com dados legados. |

A assinatura identifica os campos normalizados que o aplicativo aceitou; não é assinatura digital da FIRST nem hash de um arquivo bruto completo. A versão da API não é usada como versão do modelo. Quando a fonte não informa o modelo, o sistema mostra isso explicitamente.

## Funcionalidade, conectividade e objetividade

**Funcionalidade:** os testes cobrem idempotência, revisões, histórico antigo, resposta inválida, falha da fonte, CVE ausente, mudança de CVE, zero versus desconhecido, permissões, MFA, GET sem rede, filtros, comando com falha, exportação, backup/restauração e cache do Monte Carlo.

**Conectividade interna:** coleta validada → serviço → transação no banco → valor corrente e histórico → listagem/histórico → Monte Carlo. Em `DEBUG=0`, com banco descartável e somente o transporte externo simulado, o fluxo de EPSS, login/TOTP, páginas e estáticos WhiteNoise passou. Os testes HTTP usam a pilha Django; não constituem inspeção visual em navegador.

**Conectividade externa:** a consulta direta ao cliente FIRST foi tentada com uma CVE pública e terminou em `URLError`/falha de rede. Portanto, a ligação externa real não foi comprovada neste ambiente. O erro foi preservado como evidência, não convertido em sucesso. Os testes de integração usam respostas controladas conforme o contrato documentado da FIRST.

**Objetividade:** nenhum pacote adicional, framework de integração, serviço web paralelo ou nova árvore de permissões foi introduzido. O serviço de EPSS tem 52 linhas e a view do histórico 15 linhas, contadas incluindo comentários e linhas vazias. Reutilizamos cliente HTTP, banco, auditoria, paginação e autenticação. Migração, testes e templates ficam separados por responsabilidade; a contagem de linhas não foi usada para retirar validações ou esconder complexidade em expressões compactadas.

O estado “desatualizado” corresponde a mais de dois dias desde a data de referência em UTC (sem rejeitar dados válidos na virada do dia em outro fuso). É uma regra de apresentação explícita para dados diários, não um prazo universal de segurança. Idade e proveniência são dimensões diferentes: um valor legado pode ter data recente e ainda não ter origem registrada.

## Como usar e atualizar

1. Pare web/agendador e faça backup cifrado da instalação atual. Preserve `.env`, dados e chaves.
2. Extraia esta aplicação em uma pasta nova, configure os caminhos existentes e instale as dependências do projeto.
3. Execute `python manage.py preparar_servidor`. Isso aplica a migração **0022_historico_epss** e publica os estáticos. Não inicie o código novo contra schema antigo.
4. Execute `python manage.py sync_epss` para consultar a fonte explicitamente. Se `SAURON_ROTINAS_SEM_REDE=1`, a consulta continuará bloqueada de propósito.
5. Abra “Vulnerabilidades”. Use o filtro EPSS e o link “Histórico e origem EPSS”. Contas de leitura autorizadas podem consultar; GET não sincroniza dados.
6. Para configuração real de produção, execute também `python manage.py verificar_implantacao --json` e homologue a conectividade do servidor com a FIRST.

Dados EPSS anteriores à migração são preservados, mas não recebem origem nem histórico fabricados. Apenas uma coleta validada cria a observação associada. O comando retorna resumo e avisos em JSON; em sincronização incompleta o processo retorna código de erro. Lotes válidos anteriores podem já ter sido gravados; a atomicidade é por lote, não pela execução inteira.

## Evidências incluídas

Arquivos em `docs/evidencias/fase1/`:

- `TESTES.txt`: execução completa aprovada.
- `VERIFICACOES.txt`: lint, dependências, migrações, check de produção e estáticos.
- `BANDIT.json`: análise estática sem ocorrências.
- `ATUALIZACAO.txt`: backup no schema anterior e migração com dados preservados.
- `PRODUCAO_SMOKE.txt`: fluxo HTTP em configuração de produção sintética.
- `CONECTIVIDADE.json`: resultado da tentativa de consulta externa real.

## Limites e próximas fases

Esta fase usa a API para as CVEs do inventário local. Importação do CSV diário em grande volume, política de retenção do histórico, agendamento e alertas de mudança ficam para uma evolução específica; não se deve usar consultas individuais para espelhar todo o catálogo mundial. O histórico começa nas coletas realizadas a partir desta entrega.

O modelo do Monte Carlo permanece um cenário, com fallback sintético por CVSS quando não há EPSS e extrapolação anual sob hipóteses documentadas. Acrescentar origem e referência não valida essas hipóteses nem calibra o modelo. O estado desatualizado é mostrado e propagado aos metadados; esta fase não bloqueia automaticamente cenários com dados antigos.

Não foram executados PostgreSQL real, TLS de rede, SMTP real ou auditoria online atualizada de dependências nesta fase. Não existe alegação de ausência universal de defeitos ou de validade financeira dos resultados.

Sequência prevista:

1. **Fase 1, entregue:** EPSS, proveniência, integridade e triagem.
2. **Fase 2:** SSVC Deployer versionado, contexto local, explicação da decisão e testes da tabela oficial.
3. **Fase 3:** identidade de componentes, SBOM/VEX e deduplicação.
4. **Fase 4:** relações tipadas de rede, identidades, negócio e qualidade do inventário.
5. **Fase 5:** medidas de exposição e intervenções comparáveis.
6. **Fase 6:** Euler operacional, sensibilidade, otimização e avaliação com dados adequados.

Cada fase deve preservar a mesma disciplina: implementação pequena e coesa, testes de regras e integração, relatório de motivo/resultado e pacote completo com evidências. Nenhuma fase deve atribuir precisão a dados ou modelos que não a sustentam.

Referências do contrato externo: [FIRST — dados e formas de acesso](https://www.first.org/epss/data), [FIRST — parâmetros e resposta da API](https://api.first.org/epss/).
