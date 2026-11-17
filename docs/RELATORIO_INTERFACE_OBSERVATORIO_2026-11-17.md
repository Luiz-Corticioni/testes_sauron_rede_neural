# Interface Observatório — direção de arte e validação

## Ideia

A nova proposta combina a linguagem de um instrumento de observação antigo com a organização de um painel de segurança: fundo de pedra escura, linhas de bronze, brasa como destaque e tipografia editorial nos títulos. O astrolábio ao redor do Olho foi desenhado para o projeto em SVG e é decorativo; sua geometria não transmite dados nem indica risco. O próprio Olho continua usando o índice calculado, identificado como média e não como probabilidade.

A visão geral recebeu uma composição nova, indicadores agrupados e seções numeradas. O menu, tabelas, formulários, botões, telas de acesso e mapa usam os mesmos tokens visuais. A ajuda, o cenário fictício, os dados, as rotas e os controles existentes permanecem disponíveis. Nenhuma fonte externa, imagem remota ou dependência adicional foi introduzida.

## Referências e decisões

- [Grafana](https://github.com/grafana/grafana): organização de painéis para observação e exploração de dados; aproveitada a ideia de manter títulos, contexto e dados próximos, sem copiar a interface.
- [Security Onion Console](https://github.com/Security-Onion-Solutions/securityonion-docs/blob/2.4/introduction.rst): a visão operacional precisa conectar panorama, alertas e investigação. Os links de prioridades e do mapa permanecem diretamente acessíveis.
- [W3C, contraste](https://www.w3.org/TR/WCAG21/#contrast-minimum) e [movimento reduzido](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions): texto legível, foco visível e respeito à preferência de movimento reduzido. Isso não equivale a uma auditoria ou certificação de acessibilidade.

## Verificação

Foi usada uma base local isolada com a empresa Aurora fictícia e uma conta criada exclusivamente para o teste. O fluxo de senha e TOTP abriu o painel; foram examinados a visão geral em desktop e em viewport 390 × 844, o menu móvel, a navegação para o mapa e a presença dos indicadores. Os valores apresentados são simulados. O servidor de teste foi encerrado ao final.

A validação automatizada verifica os testes Django, JavaScript e integridade do projeto. A verificação visual foi pontual: navegadores, tamanhos de tela, tecnologias assistivas e combinações de dados ainda exigem avaliação adicional antes de qualquer declaração de conformidade.

Na primeira suíte completa, 506 dos 507 testes passaram; um teste apontou que o novo título não identificava explicitamente a visão geral de segurança. A descrição foi restaurada e os nove testes de interface passaram na nova execução. A suíte completa da revisão final deve ser conferida no CI do commit.
