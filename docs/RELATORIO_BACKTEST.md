# Backtest offline de priorização — Fase 4

**Situação em 22/11/2026:** implementação testada com dados sintéticos. Não há
resultado com dados reais neste relatório e não há evidência aqui de que uma
estratégia seja superior a outra. Os identificadores e eventos da fixture são
fictícios, apesar de terem formato de CVE.

## O que o experimento mede

O programa compara cinco formas de escolher o mesmo número de CVEs em um mesmo
universo elegível, como se todas as CVEs selecionadas fossem corrigidas no corte:

1. **CVSS:** maior nota base primeiro.
2. **CVSS + KEV:** presença no catálogo KEV histórico primeiro; depois CVSS.
3. **EPSS:** maior score histórico primeiro.
4. **SSVC:** `immediate`, `out-of-cycle`, `scheduled`, `defer`, nessa ordem.
5. **Sauron:** executa `ModeloRisco.calcular` com o perfil, a configuração, as
   incidências, dependências, exposição, KEV e CVSS ambiental declarados no
   snapshot. Ordena como a fila atual: CVSS ambiental e, depois, redução de risco
   estimada. É uma reexecução do **código atual** com dados históricos, não uma
   garantia de que aquela versão do código estava instalada no passado.

Empates usam uma ordem determinística derivada da semente. Cada CVE tem custo
de esforço igual a uma unidade, mesmo que afete vários ativos. Essa suposição
não representa automaticamente horas, custo, disponibilidade de patch ou ordem
real de implementação. Não são registradas nem executadas correções no sistema.

Para a janela posterior ao corte, são contadas CVEs com **eventos documentados**
nas fontes fornecidas. Cobertura é a fração dessas CVEs que estava na seleção;
eficiência é a fração das CVEs selecionadas para a qual houve evento documentado;
esforço é a quantidade de CVEs selecionadas. Sem evento documentado **não é**
prova de que uma CVE não tenha sido explorada. Sem eventos na janela, a
cobertura e seu intervalo ficam indisponíveis, não recebem zero.

Os intervalos de 95% são de Wilson para proporções individuais, calculados sob
uma suposição de observações independentes. Vulnerabilidades e sensores podem ser
dependentes, a amostra não é aleatória e a detecção é incompleta; portanto esses
intervalos são apenas ilustrativos. Eles não são intervalos para a diferença entre
estratégias e não provam significância ou causalidade.

## Exemplo executado: **somente dados inventados**

Fixture [backtest_sintetico.json](../tests/fixtures/backtest_sintetico.json),
corte 10/01/2025, fim 09/02/2025, semente 42 e orçamento de 2 CVEs. Das seis
CVEs fictícias, cinco têm todos os dados elegíveis no corte; uma é excluída. Há
três CVEs fictícias com eventos registrados posteriormente. Executado em Python
3.12.16, NumPy 2.3.5 e SciPy 1.18.1, sem rede.

| Estratégia | Acertos documentados / selecionadas | Cobertura observada (IC 95% Wilson) | Eficiência observada (IC 95% Wilson) | Esforço |
|---|---:|---:|---:|---:|
| CVSS | 1/2 | 33,3% (6,1–79,2%) | 50,0% (9,5–90,5%) | 2 CVEs |
| CVSS + KEV | 1/2 | 33,3% (6,1–79,2%) | 50,0% (9,5–90,5%) | 2 CVEs |
| EPSS | 1/2 | 33,3% (6,1–79,2%) | 50,0% (9,5–90,5%) | 2 CVEs |
| SSVC | 0/2 | 0,0% (0,0–56,1%) | 0,0% (0,0–65,8%) | 2 CVEs |
| Sauron | 2/2 | 66,7% (20,8–93,9%) | 100,0% (34,2–100,0%) | 2 CVEs |

**Esses números foram escolhidos para testar o software e não mostram desempenho
real.** Os intervalos são amplos e não permitem concluir que uma estratégia vença
outra, mesmo que os dados fossem representativos.

## Executar no seu computador

Instale as dependências do projeto e, no diretório do Sauron, execute:

```bash
python scripts/backtest_priorizacao.py tests/fixtures/backtest_sintetico.json --orcamento 2 --seed 42
```

O comando de gestão é equivalente:

```bash
python manage.py backtest_priorizacao tests/fixtures/backtest_sintetico.json --orcamento 2 --seed 42
```

Para salvar, acrescente `--saida resultado-backtest.json`. O arquivo deve ser novo:
o comando não sobrescreve arquivos existentes. A saída informa seleção por
estratégia, exclusões, contagens, métricas, intervalos, versões de Python/NumPy/
SciPy e SHA-256 da entrada e de trechos do código. Guarde também o commit e as
fontes originais: esses hashes não incluem todo o ambiente nem provam integridade
ou autenticidade das fontes. A saída pode conter IDs de vulnerabilidades e nomes
de fontes sensíveis; proteja-a e não a publique sem revisão.

## Preparar seus dados históricos

O programa não baixa fontes e não acessa o banco da aplicação. Monte manualmente
um JSON UTF-8 no formato da fixture, no máximo 10 MiB. É necessário normalizar as
fontes para esse formato; o programa **não importa automaticamente** os arquivos
brutos oficiais.

- `corte` e `fim`: datas ISO. O corte é o fim do dia UTC; a janela é
  `corte < observado_em ≤ fim`. Normalize as datas das fontes em UTC; não há
  precisão intradiária.
- `fontes`: identificações e versões não vazias para inventário, CVSS, EPSS,
  KEV, SSVC e exploração. Registre hashes dos arquivos originais fora do JSON ou
  inclua-os nas descrições; não inclua chaves ou dados pessoais.
- `inventario`: snapshot com `observado_em` e `disponivel_em` até o corte;
  `modelo_sauron` contém `perfil` (`puro` ou `operacional`) e `kappa` do
  cenário. `ativos` contém IDs e fatores de exposição; `incidencias` liga IDs
  distintos de incidência, ativo e CVE ao status; `dependencias` tem origem
  `dependente`, `fornecedor` e `peso` entre 0 e menor que 1. O grafo deve passar
  pelas mesmas verificações de estabilidade do modelo. Use um snapshot real;
  o estado atual não comprova como o inventário era no passado. O fator deve ser
  o efetivamente aplicado naquele contexto, incluindo os multiplicadores relevantes.
- `kev`: catálogo declarado completo, `disponivel_em` até o corte e lista de
  CVEs com `adicionada_em`. Datas de adição posteriores ao corte são ignoradas.
  Uma cópia atual filtrada por essa data não comprova a versão histórica do
  catálogo nem preserva eventuais retificações; prefira uma cópia arquivada.
- `vulnerabilidades`: uma linha por CVE/ID Sauron, com observações `cvss`,
  `cvss_ambiental`, `epss` e `ssvc`. Cada uma exige `valor`, `observado_em` e
  `disponivel_em`; nenhuma observação posterior ao corte entra no ranking.
  Informe o **maior CVSS ambiental dos ativos elegíveis daquela CVE** no snapshot;
  quando o modelo histórico usou a nota base como fallback, registre a própria
  nota base como valor ambiental e documente a razão. Não invente esse campo.
  SSVC exige ainda `revisar_em` posterior ao corte e `contexto_valido: true`.
  Como o SSVC do Sauron é por incidência, consolide antes para CVE usando a ação
  mais urgente das incidências elegíveis e registre essa regra e sua versão.
- `eventos_metadados`: `cobertura_ate` pelo menos igual ao fim e `extraido_em`
  igual ou posterior à cobertura declarada. Isso é uma declaração do fornecedor,
  não prova de completude da detecção. `eventos` informa `cve`, `observado_em`,
  `disponivel_em` e `fonte`. Somente eventos observados após o corte e disponíveis
  até o fim são contados; registros publicados depois são censurados.

Uma CVE é excluída **de todas as estratégias** quando falta CVSS base, CVSS
ambiental, EPSS ou SSVC utilizável no corte, ou não há incidência elegível. O
resultado lista as exclusões; isso pode introduzir viés de seleção. Use até 1.000
CVEs, 1.000 ativos e 10.000 incidências/dependências. Todos esses limites são do
experimento, não metas de capacidade da aplicação.

Para dados originais, a [FIRST descreve o histórico diário do EPSS](https://www.first.org/epss/data)
e suas versões. A [documentação do CERT/CC](https://certcc.github.io/SSVC/howto/deployer_tree/)
descreve as decisões SSVC do modelo Deployer. O catálogo KEV e outros registros
globais podem ajudar a documentar exploração, mas data de entrada no catálogo não
é necessariamente a data em que a exploração começou. Se a mesma fonte alimentar
preditor e desfecho, há dependência e possível viés: não interprete o resultado
como validação independente.

## Ameaças à validade e próximos passos

As datas, origens, cobertura do catálogo e validade de contexto são declarações de
entrada; o programa verifica coerência, não autenticidade. Há censura por atraso
de publicação, subnotificação, seleção do universo comum, viés dos sensores,
ausência de custo real e possível dependência entre CVEs. Uma seleção simulada
não altera o histórico global de exploração e não prova que uma correção teria
evitado incidentes locais. Antes de qualquer conclusão, use múltiplas janelas e
fontes independentes, preserve os snapshots e avalie também o custo efetivo.

## Testes da implementação

No Docker/Linux, a suíte completa passou com **595 testes**, incluindo quatro
ignorados por exigirem PostgreSQL. Após um ajuste da codificação da saída do
terminal, os **9 testes focados** do backtest passaram novamente. Eles verificam
igualdade com a fila do modelo, ausência de vazamento temporal, dados ausentes,
intervalos, reprodução por semente, script, comando de gestão, saída sem
sobrescrita e terminal com codificação limitada. Não foram executados testes
nativos no Windows nem testes de PostgreSQL nesta fase; tampouco foi realizado
um experimento com dados históricos reais ou verificada a CI do GitHub.
