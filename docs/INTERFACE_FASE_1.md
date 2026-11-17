# Fase 1 — base visual e sigilos

Os tokens de cor, severidade e famílias tipográficas foram centralizados em `tokens.css`, mantendo aliases usados pelos estilos anteriores. Títulos usam serifada local, o corpo usa fontes de sistema e códigos usam monoespaçada. Isso evita downloads externos e mantém uma aparência consistente offline.

O novo sprite `sigilos.svg` reúne desenhos originais para servidor, banco, endpoint, rede, aplicação, nuvem, criticidade e mapa. A tabela de ativos usa os ícones como decoração ao lado do nome textual do tipo; o losango em criticidade 4 acompanha o número e não afirma que haja vulnerabilidade crítica. A versão atual não usa símbolo copiado de outra franquia.

Os painéis, texturas, bordas e foco da proposta Sentinela foram preservados; a centralização de tokens não é uma auditoria completa de contraste. O inventário foi verificado visualmente em uma base fictícia. Para testar, acesse **Ativos** com um usuário autorizado e confira ícones, textos e foco por teclado. Os testes automatizados e análises executados nesta fase acompanham o commit; CSV e API não foram alterados.
