# Fase 3 — simulação contextual de 30 dias

## Implementação e motivo

O contrato `sauron.montecarlo/30d-v2` é independente da rota anterior. Para cada
incidência selecionada, o usuário declara faixas e origens para exploração,
alcance condicional e falha condicional de controle. O produto dos três fatores
é uma hipótese do cenário. Faixas incertas usam beta-PERT; as incertezas dos
fatores são amostradas independentemente e faixas fixas ficam
constantes. Origens são declarações, não verificações automáticas. Um caminho
completo e vigente precisa existir no perímetro de rede escolhido; caminho ausente
fica pendente, não vira probabilidade zero nem prova de isolamento. O grafo não
atribui números às faixas nem valida sua completude.

EPSS recente é exibido como contexto e entra na avaliação de qualidade, mas não
é automaticamente a probabilidade de comprometimento da organização. É possível
usar outra hipótese de exploração documentada quando EPSS estiver ausente; o dado
ausente continua indicado como tal. A [FIRST](https://www.first.org/epss/faq)
descreve o EPSS como estimativa de atividade de exploração observada em 30 dias,
sem contexto específico da empresa.

A correlação latente por fator comum, seus limites e a justificativa estão no
[ADR 017](adr/017-montecarlo-v2-causa-comum.md). A simulação preserva amostras
comuns ao comparar até cinco intervenções; apresenta perda média, P95/P99,
excedência, redução média e de P95 por custo e retorno relativo em 30 dias.
O apetite compara a proporção simulada acima do limite declarado com a tolerância;
quando há teto de perda, a comparação usa perdas após esse teto. A sensibilidade
opcional varia um tipo de fator por vez em todas as incidências selecionadas,
mantendo os demais sorteios; não identifica
causalidade ou interações. O limite de duas simulações simultâneas e o cache
existentes foram mantidos; a v2 limita também vínculos × simulações e trabalho
acumulado. O cache leva em conta premissas, contexto do grafo e ajuste local.

## Ajuste local de custos

É possível registrar, com permissões específicas, uma perda por categoria CIA
em incidente encerrado, indicando data, origem e natureza real ou simulada. A
marcação é feita pelo usuário e não comprova o evento. Apenas perdas **declaradas
reais** entram no ajuste; demonstrações são excluídas. A partir de dez perdas por
categoria, os percentis P10/P50/P90 servem como mínimo/moda aproximada/máximo da
PERT. Se faltarem dados, os percentis forem iguais ou houver mais de 5.000 registros
sem recorte, a categoria mantém os custos originais. O resultado mostra contagem,
faixas e métricas antes/depois quando houve ajuste.

Isto é uma regra heurística, não validação estatística: a mediana não é
necessariamente a moda, P10/P90 limitam o suporte e podem subestimar perdas
extremas, e dez exemplos não demonstram representatividade. As perdas registradas
podem se sobrepor ou refletir negócios distintos; a aplicação não verifica sua
origem ou comparabilidade. O modelo ainda escala custos por impactos CIA e usa a
maior perda por ativo, o que exige revisão especializada. Na comparação antes e
depois, os eventos são reproduzíveis com a mesma semente, mas a geração dos
custos pode consumir sorteios diferentes quando a distribuição muda.

## Como usar

1. Aplique `python manage.py migrate` e atualize os grupos com
   `python manage.py configurar_grupos`, se essa for a política adotada. Faça
   backup e teste a migração em cópia do ambiente antes de produção.
2. Cadastre o perímetro, seus ativos e relações de rede vigentes, além das
   incidências relevantes. Entre com MFA e acesse **Monte Carlo → simulação
   contextual v2**. Escolha origem e incidências e informe custos e faixas.
3. Opcionalmente informe apetite, custo de intervenção e sensibilidade. A tela
   aplica as mesmas faixas a todas as incidências selecionadas e aceita custos
   fixos; a API permite faixas individuais e custos PERT.
4. Para ajuste local, usuários autorizados podem acessar **Perdas financeiras**,
   registrar um incidente histórico encerrado e sua perda por categoria. Depois,
   selecione o ajuste no formulário. A tela lista apenas os 50 registros recentes;
   ainda não há fluxo gráfico de correção ou exclusão de perda registrada.

Os valores são dados financeiros sensíveis. O acesso exige permissões de incidente
de ativo e `view_perdafinanceira`; registro também exige `add_perdafinanceira`. Operadores
e auditores não as recebem por padrão; um gerente pode concedê-las explicitamente.
As páginas e a API retornam `Cache-Control: no-store`. Isso limita o cache HTTP,
mas **não impede o cache interno do servidor**: por padrão, resultados, custos e
origens podem ser guardados em arquivos no diretório de dados por uma hora, e
arquivos expirados não são necessariamente eliminados nesse instante. Proteja o
diretório e seu backup; o cache não é criptografado pela aplicação. A exportação
JSON resumida de inventário não inclui essa nova tabela de perdas.

## API e exemplo

`POST /api/montecarlo/v2/` exige sessão com MFA, CSRF e permissões de risco e
relações; ajuste local também exige leitura de incidentes e perdas. O corpo deve
ser JSON de até 256 KB. Use IDs reais do seu inventário; o exemplo é fictício:

```json
{
  "escopo": "Rede demonstrativa",
  "origem_ativo": "ATV-0001",
  "incidencias": ["INC-0001"],
  "n": 1000,
  "seed": 42,
  "correlacao": 0.2,
  "custos": {"C": [1000, 3000, 10000], "I": 500, "A": 2000},
  "fatores": {
    "INC-0001": {
      "exploracao": {"faixa": [0.01, 0.02, 0.04], "origem": "Hipótese sintética"},
      "alcance": {"faixa": [0.2, 0.5, 0.8], "origem": "Revisão de rede fictícia"},
      "falha_controle": {"faixa": [0.1, 0.2, 0.4], "origem": "Exercício hipotético"}
    }
  },
  "apetite": {"limite": 10000, "probabilidade_tolerada": 0.05},
  "intervencoes": [{"nome": "Corrigir vínculo", "incidencias": ["INC-0001"], "custo": 1000}],
  "sensibilidade": true,
  "calibrar": false
}
```

Quando faixa, origem ou caminho estão ausentes, a resposta retorna `disponivel: false` e pendências, sem
inventar probabilidades. Os resultados e fatores não são persistidos como cenário;
salve uma cópia protegida se precisar auditá-los. A API e o formulário usam a
mesma lógica de aplicação. A interface lista até 100 perímetros e 1.000 ativos e
incidências; use a API para outros itens dentro dos limites de processamento.

## Verificações e pendências

No Docker/Linux, a suíte completa passou com **587 testes**, quatro deles
ignorados por exigirem PostgreSQL. Após a suíte, foram ajustados textos e a recusa
de JSON excessivamente aninhado, com nova execução dos testes focados. Esses testes
cobrem compatibilidade com v1, correlação em exemplo sintético,
reprodutibilidade, apetite, intervenção, sensibilidade, pendências, caminho,
autorização, CSRF, exclusão de demonstrações e ajuste de custos. Ainda são
necessárias validações com dados empresariais reais, testes de desempenho do
fluxo completo, avaliação independente do método de calibração e testes em
PostgreSQL e no servidor de destino. Não foi realizada implantação nem teste de
entrega de e-mail nesta fase. O modelo não é implementação FAIR completa.
