# Melhorias da curadoria — 15/11/2026

[Curadoria e roadmap](curadoria/00-resumo-executivo.md) · [Documentação](README.md)

## Q1 — Cenário demonstrativo operacional

O comando `seed_demo --operacional` falhava porque tentava atribuir autoria a um aceite fora do contexto de usuário e criar um aceite já vencido, incompatível com as regras atuais. O teste reproduziu a falha antes da correção.

A demonstração agora usa dois usuários fictícios sem senha utilizável e os serviços de solicitação e aprovação existentes. O aceite é válido por 15 dias, com solicitante e aprovador distintos; o prazo de outra incidência continua vencido para demonstrar acompanhamento. Isso mantém as validações de autorização e segregação, em vez de forçar registros inválidos. A série, a justificativa e o alerta continuam identificados como simulação.

Testes em banco isolado verificaram execução, idempotência, proteção de base existente, autorização segregada e rollback/auditoria após erro simulado: oito testes de cenário e decisões passaram. Não aplique o seed sobre inventário real; o comando não substitui validação em produção.

## Q2 — Visibilidade das fontes (etapa inicial)

A página **Estado das fontes**, acessível pelo menu, apresenta a qualidade dos dados que já estão no Sauron: idade e validade do cache KEV, amostragem dos caches NVD, cobertura e atualidade do EPSS e, para usuários com as permissões necessárias, contagens de importação de sensores de isca. A página não acessa a internet, não altera o inventário e exige sessão autenticada, MFA e permissão de leitura de vulnerabilidades. A leitura NVD é limitada a 100 CVEs e 4 MiB por consulta; quando o resultado é parcial, isso aparece na página.

Essas informações permitem distinguir ausência, dado vencido e cache inválido sem apresentá-los como risco zero. O painel informa a última falha KEV apenas quando a rotina a registrou; o projeto ainda não mantém um histórico persistente equivalente de falhas NVD e EPSS. Assim, **não é possível afirmar que essas fontes estejam online**, e o item Q2 ainda não está integralmente concluído. O estado de um sensor também não é inferido a partir da importação.

Os testes cobrem ausência, cache recente e vencido, lista vazia, entrada inválida, limite de leitura, coerência e idade do EPSS, restrições de acesso, MFA e consulta sem rede.

## Verificação desta etapa

A suíte Django completa executou 440 testes com sucesso no Windows, incluindo os testes iniciais de Q1 e Q2. Após acrescentar uma verificação específica para o limite de leitura, os sete testes de fontes foram executados novamente e passaram. O Ruff também aprovou os arquivos Python novos. Os testes exibiram avisos esperados de testes que simulam falhas de SMTP e fontes externas, além de aviso sobre a pasta de arquivos estáticos não coletados.

O comando Docker não está disponível nesta máquina: Q3 (varredura reproduzível) e Q4 (carga de logins sob limites de container) continuam pendentes. A triagem de iscas Q5 e as etapas posteriores ainda não foram implementadas; dependem de desenho e testes próprios, inclusive uma decisão sobre retenção antes de usar dados reais. Nenhum resultado de implantação ou de integração contínua remota é presumido por este relatório.

## Atualização: ensaio com Docker instalado

A imagem foi construída e o Compose de teste respondeu; foi verificada persistência simples após reinício. O scan e os ensaios preliminares de carga revelaram pendências, descritas em [ensaio Docker e varredura](RELATORIO_DOCKER_CURADORIA_2026-11-15.md). Q3 e Q4 continuam abertos; o parágrafo anterior registra o estado antes da instalação.

## Q5 — Triagem manual de eventos de isca

Cada evento pode receber revisões de classificação com autoria e histórico preservado, sem modificar o alerta original. As observações são opções predefinidas para reduzir a inclusão acidental de segredos; não é uma caixa de texto livre. A ação e o histórico exigem permissões específicas e MFA, com auditoria transacional; os papéis padrão de operador e auditor não recebem acesso. A origem de demonstração ou operacional permanece vinculada ao sensor e não pode ser alterada após a importação.

Foram executados testes de autorização, formulário, MFA, histórico, auditoria, rollback e validação, além dos testes existentes de isca. Esta etapa não estabelece política de retenção para dados reais nem prova que outras entradas jamais contenham dados sensíveis. Antes do uso operacional é necessário definir retenção e responsáveis.

Após esta implementação, a suíte completa passou com 446 testes, a verificação de migrações não encontrou diferenças e o Ruff aprovou os arquivos Python alterados. A imagem foi reconstruída na instância Docker descartável: a migração 0030 foi aplicada, os serviços ficaram saudáveis e a rota de saúde retornou HTTP 200.

## Registro de tentativas de NVD e EPSS

O painel de fontes passou a apresentar a última tentativa e o último problema de NVD e EPSS, com data e categoria controlada, preservados em arquivos separados no diretório de dados. O registro não contém URLs, termos, chaves ou mensagens recebidas de terceiros. Não há gravação quando nenhuma consulta é realizada; resposta parcial e consulta desativada são identificadas. A falha da telemetria gera aviso no log e não interrompe a operação principal.

A indicação NVD de resposta recebida descreve somente o transporte JSON; validação específica, atualização do cache e conexão atual não são inferidas. O histórico pode estar ausente ou desatualizado se sua gravação falhar; fica no volume de dados do host e não coordena instalações com diretórios separados. O painel mantém o último problema, não uma trilha completa por CVE. Testes específicos cobriram falha, resposta parcial, recuperação, conteúdo sanitizado, arquivo inválido e falha de gravação.

## Retenção de iscas conforme decisão do usuário

A política padrão é de 90 dias, configurável pelo gerente de 30 a 180, com auditoria e validação na aplicação e no banco. Em cada rotina, IPs vencidos pelo recebimento são eliminados e revisões vencidas por sua própria data são removidas. Eventos sem revisões restantes são removidos após o prazo; um evento com revisão recente pode permanecer anonimizando o IP até a revisão vencer. Processamento limitado a 1.000 por tipo por execução, transacional e auditado sem IP. Alertas, backups e arquivos importados são preservados e exigem política independente.

Testes cobrem os limites da política, papéis, MFA, IP expirado com revisão recente, preservação de alertas, tratamento em lotes e rollback quando auditoria falha. O prazo depende do funcionamento do agendador; atrasos e fila são possíveis.

Após retenção e carga reproduzível, a suíte completa passou com 464 testes no Windows. O roteiro versionado de 100 clientes também foi executado em Compose descartável, com quatro administradores e 96 operadores; o relatório Docker registra tempos, limites e 429 em teste separado. A migração de retenção foi aplicada na prévia local após criar backup cifrado, e a saúde HTTP e dados demonstrativos foram verificados.
