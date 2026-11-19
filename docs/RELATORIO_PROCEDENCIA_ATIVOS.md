# Procedência e evidências na ficha do ativo

## Problema e mudança

Fontes sobre um ativo estavam em áreas distintas. A ficha agora reúne até cinco documentos SBOM/VEX, relatórios de scanner, relações tipadas e análises FAIR de cada categoria, quando a conta possui as permissões de leitura correspondentes. Ela distingue a data de observação do scanner da data de importação, mostra o prazo de revisão das relações e identifica cenários financeiros pela qualidade e data declaradas.

O cadastro básico apresenta suas datas de criação e atualização, com a ressalva de que a data se refere ao registro inteiro e não comprova a verificação de cada campo. Um ativo explicitamente marcado como demonstração recebe um aviso. Não foi criada uma pontuação automática de confiança: falta de informação, falta de permissão e evidência desfavorável têm significados diferentes.

## Segurança e limites

O resumo reaproveita as permissões dos fluxos originais. Não mostra fontes, nomes ou contagens de documentos/scanners, relações e cenários financeiros quando a conta não possui as permissões necessárias. Não consulta rede, não cria observações, não modifica incidências nem altera os modelos de risco. Os resultados são limitados a cinco itens por categoria e não representam um histórico completo.

A origem de cada campo individual do ativo ainda não é registrada, e os prazos de validade de scanners e documentos não foram inferidos. A tela não certifica que uma fonte é autêntica, que uma vulnerabilidade se aplica ou que o ativo esteja seguro. A próxima etapa dessa base deve permitir evidências de campos com autoria, data de observação e revisão, sem alterar automaticamente o cadastro.

## Como testar

Abra uma ficha em **Ativos** e consulte **Origens e evidências**. Compare uma conta com acesso às fontes e outra apenas com acesso a ativos. A suíte `tests.test_procedencia_ativo` cobre fontes permitidas, restrição de acesso e ausência de dados. A suíte completa passou com 522 testes Django e Ruff aprovou o código Python.

Referência: [NIST — gestão de ativos como base de segurança](https://csrc.nist.gov/pubs/pd/2026/06/25/asset-management-as-a-foundation-for-ot-cybersecur/ipd). A aplicação não declara conformidade com essa publicação.
