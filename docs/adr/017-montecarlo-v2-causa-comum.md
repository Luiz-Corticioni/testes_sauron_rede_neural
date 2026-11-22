# ADR 017 — Fator comum para cenários financeiros de 30 dias

**Estado:** implementação inicial em teste. **Data:** 21/11/2026.

## Decisão

Para cada grupo transitivo de vínculos que compartilham CVE, PURL de componente
ou uma relação no caminho declarado, usamos um fator normal comum. Para cada
vínculo, `U = Φ(√ρ Z_grupo + √(1−ρ) Z_individual)` gera o sorteio uniforme do
evento. `ρ` é a correlação das variáveis normais latentes, não a correlação dos
eventos binários ou das perdas. O parâmetro é uma hipótese informada pelo usuário;
compartilhar uma relação ou componente não mede nem comprova essa correlação.
Grupos conectados transitivamente têm o mesmo fator, uma simplificação que pode
agrupar vínculos demais. A implementação usa a CDF e a inversa normais do SciPy.
A composição de um grupo faz parte da semente do fator comum; alterar seus
membros pode mudar os sorteios desse grupo mesmo com a mesma semente do cenário.

Com `ρ = 0`, preservamos os sorteios da v1; fatores fixos equivalentes reproduzem
seu resultado. Para intervenções, os mesmos sorteios e custos são reutilizados.
Uma cópula geral com matriz arbitrária permitiria dependências mais ricas, mas
exigiria dados e validação que o projeto ainda não tem. O fator comum é simples,
reproduzível e limitado, não uma estimativa empiricamente calibrada. Correlação
positiva não garante que P95 ou P99 aumentem em todos os cenários. O teste de
cauda cobre apenas um exemplo sintético específico.

Referências: [SciPy — CDF normal](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.ndtr.html)
e [FIRST — limitações do EPSS](https://www.first.org/epss/faq). A decomposição
condicional da aplicação é uma hipótese local; o grafo fornece apenas caminhos
declarados, não probabilidades.
