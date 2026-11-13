# Interface do Sauron — branch de testes

[Início](../README.md) · [Manual de uso](GUIA_DE_USO.md)

## Objetivo e escopo

A identidade escura, o olho e os tons de carmesim permanecem, com maior prioridade para a leitura do inventário e a tomada de decisão. Esta branch altera templates, estilos e JavaScript da interface; não altera modelos, migrações, regras de risco, MFA, auditoria ou serviços de autenticação.

A referência visual foi direcionada por padrões de navegação, tabelas e painéis acessíveis, sem copiar código de outros projetos. Não foram adicionadas dependências externas, fontes, CDN ou dados de demonstração ao banco do usuário. A montanha e efeitos dramáticos do prompt original não foram implementados: não há fonte confiável única para classificar da mesma maneira salas, ativos, alertas e vulnerabilidades, e o usuário optou por identidade mais discreta.

## Navegação e componentes

- O menu mantém os grupos existentes e remove números decorativos. Os links são renderizados conforme as permissões relevantes; o servidor continua sendo a autoridade de acesso. A busca filtra somente os links já renderizados, sem consultar banco ou alterar permissões, aceita acentos e informa quando não encontra seções. Sem JavaScript, o menu completo renderizado continua disponível.
- A busca faz parte da navegação por teclado, inclusive no menu móvel. O botão de abrir, fechar, Escape, indicador da página e foco visível permanecem. Verificação em leitor de tela e dispositivo móvel real continua necessária.
- O painel inicial usa um topo compacto, métricas e acesso às prioridades. "Ativos cadastrados" não significa monitoramento ou detecção automática. A lista de prioridade usa os cálculos existentes, sem mesclar ou inventar KEV, EPSS ou SSVC.
- Dados ausentes não são apresentados como índice zero. O olho informa índice indisponível quando o modelo não retorna índices. O estado do serviço descreve apenas resposta, limite ou ausência de resposta do endpoint, sem declarar que banco, SMTP ou outros serviços estão saudáveis.
- A tela de certificados distingue ausência de permissão de uma lista vazia. Erros, campos, tabelas, alertas e botões usam o estilo compartilhado também em login, MFA e Monte Carlo; os formulários e regras de segurança não foram alterados. Alertas recentes mostram o valor numérico de severidade, sem inventar rótulos não definidos no modelo.
- Removidas animações contínuas de partículas, respiração do olho e fumaça decorativa. O olho conserva as alterações existentes de índice quando há dado e de simulação, sem gerar números novos. A preferência `prefers-reduced-motion` também reduz transições e rolagem suave.

## Continuação: cadastros, MFA e análise financeira

- As tabelas de ativos, vulnerabilidades e alertas possuem legendas e identificam cabeçalhos de coluna; estados vazios orientam a revisar os filtros, sem sugerir cadastro a uma conta sem permissão.
- O formulário compartilhado apresenta um aviso quando há erros e usa os identificadores esperados pelo Django para associar mensagens de erro e ajuda aos campos. Grupos de opções usam `fieldset` e `legend`; erros de campos ocultos continuam visíveis. A validação permanece a mesma do servidor.
- Quando o e-mail está indisponível ou não configurado, a seção do aplicativo autenticador começa aberta e explica o código atual e a conferência do relógio. Os métodos, senhas, CSRF e a verificação de segundo fator não foram modificados.
- A tela financeira tem atalhos para resumo, contexto, comparação e hipóteses. São somente links internos; não alteram parâmetros ou resultados da simulação.
- Verificação da continuação: 399 testes Django passaram na suíte completa e 25 testes direcionados de interface, MFA e Monte Carlo passaram em rodada posterior, incluindo os vínculos `aria-describedby`, erros em campos ocultos, a apresentação do TOTP e os destinos dos atalhos; passaram também os testes JavaScript existentes e Ruff.

## Tokens, texto e contraste

O ponto de entrada é `sauron.css`; `interface.css` complementa o estilo por componente e responsividade. `--abismo` define o fundo, `--carvao` a navegação, `--painel` a superfície, `--osso` o texto principal, `--cinza` o texto secundário, `--incandescente` links e foco, e os demais tokens de cor mantêm a identidade e o uso existente de severidade. A interface usa fontes do sistema; nenhuma fonte externa é necessária. Os tamanhos de rótulos, botões e tabelas foram ampliados.

Contrastes calculados com as cores sólidas indicadas (não representam uma auditoria de todos os estados/renderizações):

| Elemento | Frente / fundo | Razão aproximada |
|---|---|---:|
| Texto principal no painel | `#efe9e1` / `#12151a` | 15,17:1 |
| Texto secundário no painel | `#b9c1cb` / `#12151a` | 10,06:1 |
| Texto de botão principal | `#efe9e1` / `#7a0a14` | 9,26:1 |
| Indicador de foco no painel | `#ffd2a0` / `#12151a` | 13,05:1 |
| Borda de campo / fundo do campo | `#8995a4` / `#0b0d10` | 6,39:1 |
| Borda de botão / painel | `#d87d84` / `#12151a` | 6,26:1 |

O texto de severidade deve sempre ser explícito; não depender exclusivamente das cores ou do olho. Não se deve acrescentar `data-severidade` apenas para decoração nem inferir um rótulo diferente do valor de origem. `prefers-contrast: more` fortalece textos e bordas. Novos componentes precisam de contraste e foco avaliados nos seus estados e fundos reais.

## Verificações e limitações

Antes das alterações, passaram 392 testes Django, os testes JavaScript existentes e Ruff na cópia de trabalho. Após as alterações, passaram 396 testes Django na suíte completa; uma rodada direcionada posterior aprovou 20 testes de interface, MFA e Monte Carlo. Passaram ainda 6 testes pytest, os quatro testes JavaScript (menu, olho, infraestrutura HTTP/saúde e painel financeiro), Ruff e `collectstatic` com manifesto de arquivos em uma pasta isolada. A branch adiciona esses testes de JavaScript à CI. Os testes JavaScript usam ambientes simulados, não um navegador real.

Uma tentativa de inspeção visual foi interrompida pela ferramenta de controle do computador porque não conseguiu verificar o endereço da janela. Uma segunda tentativa, com prévia sintética isolada no navegador integrado, terminou em erro de conexão. Não foi feito teste visual em navegador real, nem se concluiu auditoria WCAG ou testes em larguras 360 px e 1920 px com tecnologia assistiva. Os testes automatizados e pares de cores calculados não substituem esses testes. A CI do commit inicial da branch passou em Ubuntu e nos instaladores Fedora, Rocky, Ubuntu e Windows, mas a suíte geral Windows repetiu duas falhas conhecidas de concorrência em perímetros e relações; essas regras não foram alteradas pela branch visual.
