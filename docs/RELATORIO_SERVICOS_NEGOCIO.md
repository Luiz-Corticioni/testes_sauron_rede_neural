# Serviços de negócio e perímetros de ativos

## O que mudou e por quê

O menu **Serviços de negócio** reúne serviços declarados, com responsável, descrição, impacto estimado de interrupção, criticidade e objetivo de recuperação opcional em horas. Cada serviço referencia um perímetro existente de relações, evitando manter uma segunda lista de ativos. A ficha mostra os membros do perímetro e, quando autorizada, as incidências cadastradas nesses ativos; também oferece acesso à revisão de cobertura da camada de negócio.

O objetivo de recuperação e o impacto são declarações humanas, não garantias, resultados de testes nem cálculos financeiros. A associação de um ativo ao perímetro não comprova que o serviço depende dele em todas as circunstâncias, que uma CVE o afeta ou que existe um caminho de ataque. Serviços e perímetros podem compartilhar ativos. São exibidos até 100 serviços, 100 membros e 50 incidências na ficha.

## Permissões e consistência

A consulta exige permissões de leitura do serviço e da cobertura de relações já adotadas pelo Sauron. Criar e editar exigem as permissões correspondentes; dados de incidências e CVEs exigem também suas respectivas permissões. As operações são auditadas e a edição rejeita versões antigas, preservando uma alteração concorrente. O serviço referencia o perímetro, que permanece como origem da lista de ativos.

A migração `0039_serviconegocio` cria os dados e permissões. No procedimento de atualização, mantenha o backup cifrado antes de migrar e atualize os grupos com `python manage.py configurar_grupos`, usando o executável Python ou container da instalação. O backup foi ajustado para funcionar tanto antes quanto depois dessa migração e incluir os novos registros.

## Como testar e limites

Crie um perímetro e registre seus ativos em **Qualidade das relações**; em seguida, abra **Serviços de negócio**, declare um serviço e selecione o perímetro. Na ficha, confira ativos, incidências quando autorizadas e o acesso à cobertura. Para editar, use uma conta com permissão de alteração.

Esta fase ainda não incorpora automaticamente dados de fornecedores externos, cálculo de perda por serviço, grafo visual dedicado ou uma análise completa de impacto de negócio. Mudanças no perímetro afetam todos os serviços que o referenciam; revise os vínculos e seu histórico antes de editá-lo. A lista usa limites explícitos e ainda não oferece paginação.

Foram testados cadastro, permissão, isolamento de CVEs, edição concorrente, inclusão no backup e backup anterior à migração. A suíte completa passou com 529 testes Django; o `makemigrations --check` e Ruff também passaram.

Referência: [NIST — análise de impacto de negócio para priorização de riscos](https://csrc.nist.gov/pubs/ir/8286/d/upd1/final). O recurso não declara conformidade com o NIST e não substitui uma BIA.
