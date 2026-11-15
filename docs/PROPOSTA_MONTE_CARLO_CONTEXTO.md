# Proposta: cenários financeiros com contexto empresarial

[Documentação](README.md) · [Modelo atual](../inventario/matematica/montecarlo.py) · [Caso de uso](../inventario/aplicacao/montecarlo.py)

## Objetivo e estado atual

Manter o horizonte de 30 dias e melhorar cenários de perda sem apresentar a simulação como previsão ou FAIR completo. Hoje o Sauron multiplica EPSS por um fator hipotético de exposição; usa vetor CVSS para escalonar custos de confidencialidade, integridade e disponibilidade, e utiliza CVSS/10 como aproximação quando não há vetor suportado. Agrega a maior perda por ativo e soma entre ativos, com eventos por vínculo tratados de maneira independente. Sem EPSS recente e coerente em todos os vínculos elegíveis, o serviço declara indisponibilidade. KEV é sinalizado, sem peso numérico automático. Esses métodos são hipóteses, não probabilidades locais calibradas.

## Organizar os dados por cenário, não por uma nota geral

1. **Cenário:** evento de perda específico, serviço, ativos e período; exemplo: indisponibilidade do faturamento por comprometimento de uma credencial privilegiada. Registrar escopo e exclusões.
2. **Ameaça e superfície:** frequência de tentativas relevantes (observações ou faixa estimada), exposição, alcançabilidade, dependências, fornecedores, CVEs, EPSS, KEV e evidência de exploração. EPSS descreve exploração observada de uma CVE na população, não a probabilidade do cenário atingir a empresa. Não multiplicá-lo mecanicamente por pesos arbitrários.
3. **Identidades e controles:** quantidade de contas e privilégios relevantes ao caminho, contas compartilhadas, MFA, segmentação, detecção e recuperação. Identidades são dados sensíveis; priorizar agregados e restringir acesso. Treinamento e controles só mudam probabilidades quando existir uma hipótese de eficácia documentada.
4. **Consequências:** paralisação por serviço, duração de recuperação, equipes e horas adicionais, custos de fornecedores, restauração, resposta e notificações, quando aplicáveis. Valores monetários, período, moeda e origem devem ser claros. Receita interrompida não é automaticamente lucro perdido; evitar contar salário, paralisação e interrupção duas vezes.
5. **Relações:** registrar quais serviços dependem de quais componentes, sua criticidade para o processo e pontos únicos de falha. Compartilhamento de provedores e credenciais pode correlacionar eventos; ausência de relacionamento é dado desconhecido, não prova de isolamento.
6. **Software e linguagem:** versão, bibliotecas, suporte, composição e CVEs são dados úteis. Linguagem isolada não é uma vulnerabilidade nem deve gerar penalidade automática; relacionar falhas reais e contexto de implantação.

Cada entrada deve informar unidade, origem, data, responsável, intervalo plausível e confiança ou justificativa. Não preencher o que falta com zero; sinalizar lacuna e permitir comparar cenários hipotéticos explicitamente identificados.

## Matemática proposta

- Separar frequência de eventos e consequência financeira por evento. Para cada execução, sortear entradas de frequência e magnitude a partir de dados medidos ou faixas justificadas; PERT ou triangular só quando mínimo, valor típico e máximo fizerem sentido. Registrar sementes, algoritmo e versões.
- Representar serviços e dependências como grafo/matriz de adjacência e atributos como vetores por ativo ou serviço. A matriz descreve relações; ela não fornece probabilidade de propagação por si só. Probabilidades condicionais ou faixas de transição exigem evidência, julgamento documentado e validação.
- Amostrar eventos compartilhados por fornecedor, identidade ou infraestrutura quando pertinente; não somar perdas do mesmo incidente duas vezes. Considerar correlação por cenários comuns antes de adotar uma matriz estatística sem dados para estimá-la.
- Pesos podem servir para **triagem explicável**, com escala e origem documentadas; não transformar uma pontuação ponderada em probabilidade ou reais sem calibração. Contagem de funcionários, níveis de acesso e linguagem não têm coeficientes universais.
- Apresentar média, mediana, percentis, probabilidade simulada de ultrapassar um limite e análise de sensibilidade. Um P95 é percentil condicional às premissas do modelo, não um intervalo de confiança empírico nem valor garantido.

## Etapas e critérios

1. Identificar dados já existentes e elaborar questionário por cenário com responsáveis; manter teste em empresa fictícia.
2. Implementar entrada de custo e duração com unidades, proveniência, faixas, validação e identificação de lacunas; preservar o modelo atual e versionar a alternativa.
3. Simular um único cenário de interrupção com frequência e custos explicitamente informados, comparar antes/depois de controles e impedir dupla contagem; não derivar probabilidade local diretamente do EPSS.
4. Acrescentar grafo de dependências e cenários compartilhados; testar rede desconectada, ciclos, dependência comum e contagem única de perdas.
5. Validar com casos sintéticos reprodutíveis, sensibilidade, valores extremos, limitações computacionais, permissões e regressão; comparar com histórico real apenas quando existir e com autorização. Não chamar calibrado antes de validação.
6. Acrescentar visualização executiva: hipótese, fonte, data, intervalo de perdas, fatores que mais influenciam o resultado e pendências; distinguir comparação de controles de promessa de economia.

Referências: [FIRST EPSS](https://www.first.org/epss/), [NIST SP 800-30 Rev. 1](https://csrc.nist.gov/pubs/sp/800/30/r1/final), [FAIR Institute — fontes de dados](https://www.fairinstitute.org/hubfs/FAIR%20CRM%20Body%20of%20Knowledge/FAIR%20Institute%20--%20Analysts%20Guide%20to%20Cyber%20Risk%20Data%20Sources%20%28May%202025%29.pdf).

Esta é uma proposta de desenho. Nenhuma fórmula nova, coeficiente, calibração, estimativa de perda ou garantia foi implementada neste documento.
