# Interface — fase 5: exploração do painel

O painel oferece seleção por tipo, responsável, zona de rede, faixa de CVSS e pendências, além de atalhos a partir das distribuições. O recorte tem seus próprios totais, gráfico, prioridades de ativos e matriz de incidências. O Olho permanece global e está identificado como tal; os valores de risco dos ativos escolhidos são calculados na rede completa, pois dependências externas ao recorte continuam relevantes. As demais seções globais retornam ao limpar o filtro, evitando apresentar seus números como resultados filtrados.

A atividade recente usa registros reais e exige permissão de auditoria. O controle de quantidade de eventos tem alternativa sem JavaScript. Mitigações e correções são extraídas de transições de situação registradas, não inferidas de uma edição genérica. A tendência usa até 30 amostras existentes do perfil selecionado, exige permissão para consultá-las e identifica os registros de demonstração. Não é previsão. Os totais do recorte de CVSS abrangem todas as incidências dos ativos selecionados, explicitamente informado na tela.

A paleta Ctrl+K usa diálogo nativo e links fornecidos pelo menu autorizado; também encaminha a pesquisa para a lista de ativos quando a permissão permite. Nenhum privilégio é concedido pela paleta. Foram mantidos os links e cálculos anteriores.

Limites: o recorte substitui temporariamente as seções globais, em vez de recalcular cenários financeiros ou projeções de correção sobre uma rede incompleta. O histórico do recorte não possui amostras históricas por filtro; por isso a tendência global só aparece sem filtros. As opções de responsável e zona exibem os primeiros 200 valores distintos. O histórico e a matriz possuem limites explícitos.

Verificações: 519 testes Django aprovados, incluindo escopo, cache compartilhado, permissão de auditoria e amostras; testes JavaScript existentes e Ruff aprovados. A paleta e o recorte foram inspecionados no navegador com dados de demonstração. Para testar, execute o servidor, entre com conta autorizada, aplique filtros na visão geral e pressione Ctrl+K.

Referência de acessibilidade: [W3C — diálogos HTML](https://www.w3.org/WAI/WCAG22/Techniques/html/H102).
