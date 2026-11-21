# Fase 2 — explicabilidade e mudanças

## O que foi feito e por quê

A tela de prioridades e `GET /api/risco/` apresentam a decomposição do ganho
estimado de cada vulnerabilidade. O cálculo passa a registrar a contribuição
direta nos ativos afetados e a parcela adicional propagada pelas dependências,
usando os mesmos vetores e o mesmo sistema linear que produzem o resultado.
Os valores de apresentação são arredondados; somas de muitos valores arredondados
individualmente podem diferir ligeiramente do total. O JSON inclui os ativos e
fatores de exposição utilizados diretamente, a severidade e o multiplicador KEV.
A tela mostra os primeiros dez ativos; o JSON contém a relação completa.

No perfil puro, exposição e KEV não modificam o cálculo; no operacional, aplicam-se
os fatores configurados e KEV. CVSS ambiental é chave de ordenação quando há
valores calculados, não a severidade multiplicada para o ganho. EPSS, SSVC e
criticidade de serviço **não são utilizados na fórmula atual**; a resposta os
identifica como não utilizados. A criticidade dos ativos influencia outro
indicador do relatório, não esta redução. O modelo não prova alcance real ou
probabilidade de comprometimento.

Os novos snapshots do perfil puro guardam também o top 10 de vulnerabilidades
com redução positiva, a contagem de incidências abertas ou em tratamento com SLA
vencido e o MTTR dos ciclos corrigidos registrados. A página inicial e
`GET /api/v1/risco/mudancas/` comparam os últimos dois snapshots, incluindo a
variação do risco total. O MTTR não inclui mitigações como correção; valores sem
ciclos conhecidos ficam indisponíveis. Snapshots antigos sem esses dados não são
preenchidos retroativamente. A comparação é entre registros históricos, não entre
o último registro e o estado atual; o recorte é global e o perfil é puro. A tela
identifica registros de demonstração. A consulta exige sessão com MFA e permissões
de risco, snapshots e histórico de incidência.

A migração `0042_snapshotrisco_detalhes` acrescenta um campo opcional; aplique
`python manage.py migrate` antes de iniciar a versão atualizada. Para gerar um
novo ponto, execute `python manage.py snapshot_risco` no ambiente da aplicação.
Cada execução registra um ponto. É preciso ter dois novos
registros para comparar fila, backlog e MTTR; registros anteriores permitem
comparar apenas o risco total. Os itens podem entrar ou sair do top por mudança
de risco, ordenação ou inventário, não necessariamente por correção.

## Verificação e limitações

Os testes focados exercitam o cálculo nos dois perfis, a comparação com a
simulação de correção, as permissões, o caso de snapshots antigos e os novos
registros, incluindo recusa para usuários sem autenticação, MFA ou permissão.
A suíte completa executou 573 testes em Linux no Docker: passou com quatro
testes de PostgreSQL ignorados. Após o acréscimo das verificações de autenticação,
os quatro testes focados da fase também passaram no mesmo ambiente. A tentativa
de teste nativo no Windows não iniciou por falta de dependências no interpretador
local; não houve execução completa no Windows nem CI do GitHub nesta branch.
A checagem de migrações não encontrou alterações pendentes. A especificação
OpenAPI foi validada com `openapi-spec-validator`. A cobertura histórica de EPSS, SSVC,
criticidade de serviço e dependências específicas não existe nos snapshots antigos.
A fase anterior permanece com suas pendências documentadas; esta etapa não as
transforma em concluídas.
