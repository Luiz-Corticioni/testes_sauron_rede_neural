# Interface — fase 6: acessibilidade e desempenho

O botão **Reduzir efeitos**, no topo, guarda a escolha no navegador. A preferência do sistema operacional por movimento reduzido também é respeitada; quando o armazenamento local estiver bloqueado, o botão continua funcionando durante a página atual. A opção reduz animações, transições, contadores animados e o parallax, sem impedir o aviso textual de novas incidências. A navegação entre páginas usa View Transitions quando disponível e mantém o comportamento convencional em navegadores sem suporte.

A arte principal foi convertida de PNG para WebP mantendo 1.672 × 941 pixels: 1.877.612 para 83.588 bytes, aproximadamente 95,5% menos para a transferência da imagem. O original permanece no histórico Git. As dependências do grafo são locais e carregadas apenas na página do mapa; seu layout é limitado a 60 nós. A entrada dos cartões usa apenas transformação e opacidade, respeitando a redução de movimento.

Foram medidos três pares de cores usados na busca e na matriz: 15,08:1, 10,34:1 e 8,68:1. A paleta usa diálogo nativo, o mapa mantém tabela alternativa e a severidade é acompanhada por texto ou valores. Estas verificações não substituem uma auditoria WCAG completa: contraste sobre imagens, ampliação, leitores de tela, dispositivos móveis e todos os estados das demais páginas ainda precisam de validação especializada. Também não foi medido desempenho em 60 fps em aparelhos modestos.

Verificações: 519 testes Django aprovados; verificações JavaScript de movimento, olho, contadores, paleta, grafo e pares de contraste; Ruff aprovado. A prévia foi conferida no navegador, incluindo a persistência da preferência após recarga e o controle da linha do tempo. Para testar, abra o painel, acione **Reduzir efeitos**, recarregue e verifique que a opção continua selecionada; repita com a preferência do sistema operacional.

Referências: [WCAG — contraste mínimo](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum) e [MDN — preferência de movimento reduzido](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media/prefers-reduced-motion).
