# Reconhecimento da interface — etapa 0

O Sauron é um monólito Django 5.2 com templates em `inventario/templates/inventario`, CSS/SVG/JavaScript locais em `inventario/static/inventario`, ORM e serviços em `inventario/aplicacao`. O painel recebe dados do banco por `contexto_painel`; o cálculo de risco usa matriz de dependências e CVSS. Os dados também chegam por importação CSV e fontes externas com atualização explícita. A API v1 de ativos e equipamentos por vulnerabilidade, `/api/risco/`, `/api/impacto/` e `/api/grafo-relacoes/` preservam as permissões e contratos existentes.

As telas de inventário, incidências, fontes, mapa, análise financeira e FAIR já existem. O mapa SVG tem tabela alternativa e limite de 60 nós; a interface possui desenho local do Olho, menu móvel, mensagens, login e MFA. Há uma base fictícia isolada com produtos reais e uma proposta visual em `observatorio.css` e `sentinela.css`. Esses componentes serão evoluídos, sem mudar de framework, reescrever a aplicação ou alterar importação CSV.

Premissas: símbolos novos serão originais, sem reproduzir marcas de terceiros. Risco matricial e alcance do grafo não provam exploração nem são probabilidades. Estados de fonte serão derivados de indicadores explícitos, com incerteza quando não houver dados. Animações não serão mostradas como evidência de eventos que não foram observados. Acessibilidade e limites de dados terão prioridade sobre ornamentação.

Referências iniciais: [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [foco GOV.UK](https://design-system.service.gov.uk/get-started/focus-states/), [tokens do Grafana Pyroscope](https://github.com/grafana/pyroscope/blob/main/ui/DESIGN.md) e [SVG symbol](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/symbol).
