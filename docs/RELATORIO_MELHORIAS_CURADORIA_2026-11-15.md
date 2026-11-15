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
