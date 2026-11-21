# Fase 1 — qualidade e estado dos dados — 21/11/2026

**Estado: em andamento.** A base inicial da branch executou 553 testes Django
com sucesso, quatro exclusivos de PostgreSQL pulados no SQLite.

## Estado das fontes

O diagnóstico já distinguia idade, cobertura e histórico de tentativas NVD/EPSS;
a etapa acrescenta histórico sanitizado de tentativas KEV e uma síntese das
fontes com origem, data e idade dos dados locais. A síntese distingue dados
atuais, vencidos, vazios, incompletos e falha na última tentativa. Uma falha
passada não demonstra que a fonte permaneça inacessível; resposta recebida não
garante dado válido, e cache atual não comprova conectividade.

Importações manuais de scanner são apresentadas apenas a quem tem as permissões
de leitura necessárias, com origem, observação, recebimento e contagem. Não há
prazo de validade ou cobertura completa inferidos dessas importações.

`python manage.py test tests.test_estado_fontes tests.test_historico_fontes
--noinput`: 14 testes aprovados, com fontes externas simuladas. `ruff check .`
passou. Sem migração nesta etapa. Testes adicionais e suite completa ao final da
fase ainda são necessários.

## Pendente

Índices de qualidade por ativo, serviço e resultado financeiro, exposição
autorizada nas telas e APIs de risco, integração ao Monte Carlo, documentação
final e verificações integrais da fase. A medição ponta a ponta de escala e
demais pendências da Fase 0 permanecem no relatório anterior.
