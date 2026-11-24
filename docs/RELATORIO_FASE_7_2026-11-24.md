# Fase 7 — visão executiva e referências de evidência

Data: 24/11/2026. Base: branch `fase-7-visao-executiva`, após a fase 6.
Decisão arquitetural: [ADR 020](adr/020-visao-executiva.md).

## O que foi feito e por quê

O menu **Visão executiva** reúne informações para uma conversa com a diretoria:

- Até cinco serviços ordenados pela quantidade de incidências confirmadas em
  ativos operacionais dos perímetros declarados; empates pela criticidade do
  serviço. A contagem não é uma estimativa de perda nem demonstra risco zero para
  serviços ausentes.
- Uma execução FAIR guardada, selecionada pelo usuário ou a mais recente: perda
  média, P95 e faixa P5–P95 dos cenários simulados em 30 dias. A faixa não é
  intervalo de confiança da perda real. Não se somam cenários automaticamente.
  Modelo, quantidade de simulações, escopo, classificação e data das premissas
  são mostrados; ausência ou resultado inválido aparece como indisponível.
- Completude e idade das observações EPSS elegíveis, estados locais NVD/KEV,
  decisões aguardando revisão e correções com prazo vencido.
- Transições de correção e reabertura registradas nos últimos sete dias, além
  da variação do índice técnico entre o último snapshot anterior à janela e o
  último dentro dela. As datas dos snapshots aparecem: o anterior pode ser mais
  antigo que sete dias. Sem os dois registros, a comparação fica indisponível.
- Referências indicativas a inventário, vulnerabilidades, gestão de riscos e
  evidências relacionadas a ISO/IEC 27001:2022 Anexo A, NIST CSF 2.0, LGPD
  art. 46 e Resolução CMN 4.893. **Não há auditoria ou verificação de
  conformidade e o texto não é parecer jurídico.** A aplicabilidade da resolução
  depende da instituição e da regulamentação pertinente.

Fato: esses dados são extraídos de registros existentes; abrir o relatório não
executa nova simulação nem faz consulta externa. Inferência: organizá-los pode
ajudar a priorizar perguntas, mas não comprova a segurança ou a exposição real da
empresa. Dados fictícios continuam identificados como simulados quando o cenário
ou os snapshots os identificam como tal.

## Como usar e exportar

1. Cadastre serviços com perímetros e incidências, se disponíveis. Para obter
   valores financeiros, abra **FAIR**, crie um cenário e guarde uma execução.
2. Abra **Visão executiva** e selecione uma execução guardada. Confira as datas,
   o escopo, a origem das premissas e as lacunas antes de compartilhar.
3. Escolha o destino pretendido e clique em **Baixar HTML para impressão**.
   Abra o arquivo no navegador e use **Imprimir → Salvar como PDF**, se desejar.
   O HTML é formatado para A4; conteúdo comprido, escala e navegador podem
   alterar a paginação. O destino declarado registra a intenção, não impede cópia
   ou compartilhamento posterior. Proteja o arquivo como informação sensível.

A leitura exige permissões de ativos, vulnerabilidades, incidências, cenário
financeiro, serviços, perímetros, snapshots e histórico de incidências. A
exportação também exige `change_incidencia`, sessão com os controles existentes
e POST com CSRF. A operação revalida permissões após a trava, registra destino,
ID da execução e SHA-256 do HTML na trilha HMAC na mesma transação. Ela não
registra os valores financeiros nem o documento completo na auditoria. Os grupos
padrão que não tiverem todas as permissões não recebem o atalho; não se concedem
novas permissões automaticamente. Não houve migração nem dependência nova.

## Fontes dos referenciais

O mapeamento é um ponto de partida para revisão humana, não uma tradução
automática dos requisitos. Fontes consultadas em 24/11/2026:

- [ISO/IEC 27001](https://www.iso.org/standard/27001) e publicação do
  [comitê ISO sobre inventário 5.9](https://committee.iso.org/files/live/sites/jtc1sc27/files/resources/ISO-IECJTC1-SC27_N22394_SC%2027%20Journal%20Volume%202%2C%20Issue%202%20-%20Special%20issue%20on%20ISO-IEC%2027002.pdf).
- [NIST CSF 2.0](https://www.nist.gov/cyberframework).
- [LGPD, texto consolidado, art. 46](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm).
- [Banco Central — Resolução CMN 4.893, texto vigente](https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?numero=4893&tipo=Resolu%C3%A7%C3%A3o+CMN).

## Verificação e limites

- `python manage.py test --noinput`: 634 testes, sete ignorados, com código
  montado em contêiner Linux sem rede. Após essa execução, houve ajustes de
  apresentação que foram verificados nos testes focados e na impressão abaixo.
- `python manage.py test tests.test_visao_executiva --noinput`: cinco testes
  focados passaram, cobrindo resultado indisponível, valores persistidos,
  contagem, seleção temporal, autorização, revogação, CSRF, escape de HTML e
  integridade/rollback da auditoria.
- `pytest`: seis testes passaram. Ruff e Bandit passaram; Bandit apontou aviso
  já existente de anotação `nosec` no backup. Mypy passou no escopo atual de dois
  arquivos de domínio; `makemigrations --check --dry-run` não detectou mudança.
  A suíte emitiu o aviso já existente de compatibilidade futura do SciPy.
- Os onze scripts JavaScript do CI passaram. A consulta `pip-audit -r
  requirements.txt` não apontou vulnerabilidades conhecidas no momento da
  execução; novas divulgações podem alterar o resultado.
- Um relatório com cinco serviços e cenário **fictícios** foi impresso no Edge
  em A4: `pdfinfo` indicou uma página e a página renderizada foi conferida
  visualmente. Isso não garante uma página para textos mais extensos, outras
  opções de impressão ou navegadores.

Não foram testados usabilidade com stakeholders, tecnologias assistivas,
impressão com todos os tamanhos de dados, integração contínua no GitHub ou uma
implantação de produção. O relatório não substitui avaliação jurídica,
certificação de controles nem validação financeira das hipóteses.
