# Fase 6 — ciclo de remediação

Data: 22/11/2026. Branch de trabalho: `fase-6-ciclo-remediacao`.
Decisão arquitetural: [ADR 019](adr/019-remediacao-e-envio-externo.md).

## Resultado e decisões

**Fato:** o projeto já tinha SLA por criticidade e regra KEV, aceite com
justificativa, responsável e validade, e segunda aprovação de outra pessoa para
aceites sensíveis e correções/mitigações de maior gravidade. O agendador já
chama `expirar_aceites`: depois do último dia de validade, a incidência volta a
ABERTA e é gerado alerta. Esses mecanismos foram preservados e acrescentou-se
um teste do vencimento e da ausência de alertas duplicados. O agendador precisa
estar ativo; a passagem do tempo isoladamente não executa a rotina.

**Fato:** o menu de incidências oferece comparação de scan, emissão de OpenVEX
e chamados. As permissões são verificadas novamente no serviço após a trava de
escrita. A comparação e os chamados registram ações na auditoria; o envio
externo exige duas transações pois não existe transação comum com Jira/GLPI.

**Inferência:** a comparação reduz a chance de tratar uma simples ausência como
correção, mas não comprova cobertura do scanner nem a identidade real do ativo.

## Comparar evidências

Habilite a importação da fase 5, aplique as migrações e conceda as permissões
de leitura e adição de observações/sugestões necessárias. Em **Incidências →
Comparar scan**, informe o número de uma observação Trivy revisada como válida,
fonte e versão declaradas iguais às anteriores, data posterior com fuso, e um
novo relatório JSON Trivy SchemaVersion 2. O arquivo precisa conter o mesmo
`Target`, uma lista explícita `Vulnerabilities` e não conter a CVE nesse alvo.
O operador declara a associação do alvo ao ativo e a comparabilidade do escopo.

O resultado é uma sugestão registrada com hash do arquivo, data declarada,
origem anterior e responsável. A incidência **não muda de status**. A pessoa
responsável precisa examinar evidências e usar o fluxo de edição/aprovação.
O arquivo original não é retido. Dado vazio, alvo diferente, campo ausente,
relatório truncado ou CVE ainda encontrada não são aceitos como sugestão.

Limitações: somente esse perfil Trivy; o relógio, a origem, a associação ao
ativo e a cobertura são declarados, não autenticados. A ausência de detecção
pode resultar de versão, configuração ou limitações do scanner, aliases ou
relatório incompleto que ainda seja sintaticamente válido. O Trivy pode omitir
`Vulnerabilities` em saídas vazias: tais arquivos são recusados, não presumidos
como resultados limpos. Ainda não há verificação equivalente para os outros
importadores. O histórico de sugestões não possui política automática de
retenção; defina-a antes de usar dados reais.

## Chamados Jira e GLPI

Ambas integrações vêm desativadas e nenhuma conexão ocorre ao abrir a página.
O usuário autorizado escolhe o sistema e confirma o POST em **Incidências →
Chamados**. Apenas ID de incidência, CVE (ou ID interno) e prazo são enviados;
o conteúdo de evidências não é transmitido. URLs e credenciais são definidas
por administradores do servidor, não pela tela. HTTPS é obrigatório; o cliente
recusa redirecionamentos e limita o tempo e o tamanho da resposta.

Para um ambiente de teste autorizado, configure variáveis no servidor e reinicie:

- Jira Cloud: `SAURON_TICKETS_JIRA_ENABLED=1`, `SAURON_JIRA_URL`,
  `SAURON_JIRA_USER`, `SAURON_JIRA_API_TOKEN`, `SAURON_JIRA_PROJECT` e
  `SAURON_JIRA_ISSUE_TYPE`. A conta deve ter somente as permissões necessárias.
- GLPI API legada: `SAURON_TICKETS_GLPI_ENABLED=1`, `SAURON_GLPI_URL`,
  `SAURON_GLPI_SESSION_TOKEN` e `SAURON_GLPI_APP_TOKEN`. Exige sessão já
  provisionada; esta implementação não renova o token de sessão. A API, perfil,
  configuração e versão do servidor precisam ser homologados.

Não versionar credenciais nem enviá-las para mensagens. O servidor externo e
seus operadores recebem os dados enviados; avalie o destino antes da ativação.
Não inclua `/rest/api/3/issue` ou `/apirest.php/Ticket` na URL base. O Jira pode
exigir campos adicionais específicos do projeto, que este adaptador não fornece.

Antes de solicitar, é gravado um registro `ENVIANDO`; depois, `CRIADO` com ID ou
`INCERTO`, sem detalhes da resposta nem segredo. Um timeout pode ocorrer após o
servidor externo criar o chamado. Por isso, não há repetição automática e existe
no máximo uma tentativa por incidência e provedor. Se o processo parar ou se a
auditoria falhar depois da chamada, o estado pode permanecer em `ENVIANDO`.
Consulte o sistema externo e a auditoria antes de qualquer medida manual. Não há
interface automática de reconciliação ou reenvio; novas rodadas de tratamento
da mesma incidência também exigem procedimento administrativo futuro.

Os adaptadores seguem o perfil [Jira Cloud REST v3](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/) e o perfil da API legada GLPI; não se afirma compatibilidade com todas as versões e configurações.

## OpenVEX

Em **Incidências → Emitir VEX**, o usuário deve declarar o autor e confirmar o
conteúdo. São aceitas somente incidências `CORRIGIDA` com decisão concluída,
evidência, CVE e componente de software identificado por PURL exata e versão.
O arquivo inclui a evidência como `status_notes`: examine dados internos antes de
compartilhar. O estado `fixed` é uma declaração, não comprovação independente.
Aceites e mitigações não são convertidos em correção; emissão de outros estados
permanece pendente. A exportação é auditada pelo hash e ID, sem gravar o arquivo.

O esquema [OpenVEX 0.2.0](https://github.com/openvex/spec/blob/93139bd2c65390b504e47f82f11c50451289f93a/openvex_json_schema.json)
foi copiado para `docs/exemplos/openvex-schema-v0.2.0.json` (SHA-256
`9373597734ed1d3ea5161a8b46d3866c4a8cfe76fd632fdd16aef01fb34b3238`).
A licença CC0 do esquema acompanha o arquivo. É usado `jsonschema==4.26.0`,
licença MIT, para validação local Draft 2020-12, sem resolver URLs. A dependência
inclui transitivas; não há verificação independente do significado dos dados
nem validação adicional de todos os formatos IRI pelo `FormatChecker`.

## Fatos da validação

- `python manage.py test --noinput`: 629 testes, sete ignorados, na imagem
  Linux final sem rede. O novo teste de concorrência PostgreSQL foi executado
  separadamente como descrito abaixo.
- `python manage.py test tests.test_remediacao tests.test_tickets_remediacao tests.test_remediacao_operacao --noinput`:
  22 testes passaram sem rede, inclusive na imagem reconstruída com as
  dependências finais. Em SQLite, a limpeza exclusiva do banco de testes
  remove e restaura temporariamente o trigger de exclusão de auditoria.
- Em PostgreSQL 16 descartável sem portas publicadas e sem rede externa, duas
  requisições simultâneas geraram um registro e um único envio simulado; a cadeia
  HMAC foi verificada. A primeira tentativa falhou porque o banco de laboratório
  não tinha TLS; a repetição usou `sslmode=disable` apenas na rede local isolada.
- `pytest` executou seis testes; Ruff, Bandit, mypy no escopo de dois arquivos
  de domínio e `makemigrations --check --dry-run` passaram. Bandit informou o
  aviso anterior sobre `nosec` em backup. A suíte também informou FutureWarning
  existente de SciPy. `pip-audit -r requirements.txt` não encontrou
  vulnerabilidades conhecidas no momento da consulta.
- Onze scripts JavaScript do CI passaram, assim como o validador da
  especificação OpenAPI e o diagnóstico `check_producao.py`. A resolução conjunta
  de `requirements.txt` e `requirements-dev.txt` foi conferida com `pip install
  --dry-run`; inicialmente houve incompatibilidade entre versões de jsonschema e
  do validador OpenAPI, corrigida ao alinhar a dependência para 4.26.0.
- O teste SMTP local do CI passou com servidor simulado; não enviou mensagens
  para a internet nem verificou uma conta real.
- A imagem `sauron-fase6:validacao` foi construída; confirmou-se nela a presença
  da biblioteca de validação e do esquema. A construção usa atualizações e
  dependências disponíveis no momento, inclusive transitivas não fixadas.
- Trivy 0.76.2 analisou uma exportação temporária da imagem, com banco atualizado
  e filtro HIGH/CRITICAL, retornando código 0 e sem achados nessas severidades.
  A consulta é uma fotografia da base e da imagem no momento da execução; não
  cobre vulnerabilidades ainda desconhecidas nem prova segurança da implantação.

Não foram feitas chamadas reais a Jira/GLPI, homologação com arquivos de clientes,
validação Windows nativa nem execução do workflow GitHub. Portanto, integração
em produção, acessibilidade integral e ausência
de vulnerabilidades não foram demonstradas. Consulte o administrador e teste
num projeto externo de homologação antes de ativar os conectores.
