# ADR 020 — Resumo executivo baseado em evidências existentes

Status: implementado; 24/11/2026.

## Contexto

Diretorias precisam comparar pendências, decisões e cenários financeiros sem
interpretar um índice técnico como probabilidade de perda ou presumir que uma
aplicação comprova conformidade jurídica. Resultados antigos ou incompletos não
podem ser preenchidos com valores inventados. Uma exportação pode revelar
informações sensíveis e exige autorização e trilha verificável.

## Decisão

Oferecer uma tela e uma exportação HTML imprimível, reaproveitando apenas dados
persistidos. A lista de serviços usa contagem explícita de incidências por
perímetro; a execução FAIR é selecionada, sem agregar cenários ou disparar uma
simulação. A faixa P5–P95 descreve percentis de simulações, não intervalo de
confiança da perda real. A variação técnica usa snapshots datados antes e dentro
da janela de sete dias. Quando faltam dados, o relatório informa indisponibilidade.

O mapeamento dos referenciais é indicativo e descreve possíveis evidências; não
atribui conformidade. A exportação exige destino escolhido, POST com CSRF e
permissões revalidadas após trava; o hash do HTML e o destino são auditados na
mesma transação. A escolha de destino não controla o arquivo depois do download.

## Consequências

Uma execução selecionada representa um cenário, não o risco financeiro total da
empresa. A lista de incidências não estabelece efetividade dos controles nem o
grau de comprometimento dos serviços. Os snapshots podem ter idades diferentes,
explicitadas no relatório. O HTML contém dados financeiros e operacionais e deve
ser protegido pelo destinatário. A impressão é ajustada para A4, mas conteúdo
extenso, navegador e escala podem exigir mais de uma folha. Não há declaração
jurídica, auditoria de conformidade ou validação empírica das simulações.
