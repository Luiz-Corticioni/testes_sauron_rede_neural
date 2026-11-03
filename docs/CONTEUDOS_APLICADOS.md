# Conteúdos aplicados ao Sauron

Análise de `Documento sem título.md`, fornecido pelo estudante, e dos requisitos do
Trabalho 2. O material contém 21 blocos, mas 20 tópicos distintos: S3_04 aparece duas
vezes. Esta revisão aplica os conceitos que melhoram o inventário e documenta os
exercícios que devem continuar em atividades de estudo separadas.

## Critério de escolha

Uma adição deve responder a uma pergunta do inventário, aproveitar os dados já
cadastrados, funcionar no terminal e no site e ser explicável sem esconder suas
limitações. Acrescentar um menu de Fibonacci, um simulador de portas lógicas ou um
segundo servidor Flask aumentaria o código sem melhorar a gestão dos ativos.

Foram escolhidos dois recursos: **alcance completo das dependências**, para saber
quem pode ser afetado por um fornecedor, e **conferência explicada do cálculo**, para
entender e verificar o risco exibido. As subclasses também passaram a explicitar
seus detalhes por sobrescrita. Não há dependência nova nem migração SQL nesta revisão.

## Relação com as atividades do material

| UID | Conteúdo | Decisão e localização atual |
|---|---|---|
| S3_01 | POO, herança, sobrescrita, `super`, `isinstance`, JSON com tipo | Aplicado em `dominio/equipamentos.py`. Servidor, Notebook e Roteador sobrescrevem `exibir_detalhes`. A conferência matricial percorre os objetos reais de forma polimórfica. A fábrica e os vínculos JSON existentes foram preservados. |
| S3_02 | Recursão, memoização, programação funcional | Dicionários, compreensões e funções de ordenação já são usados. A nova busca é iterativa para evitar limite de pilha. Fatorial, Fibonacci, `map/filter/reduce` e sua comparação de tempos ficam como exercício separado. Cache de resultados não é uma implementação de Fibonacci memoizado. |
| S3_03 | TAD, fila FIFO, deque, listas encadeadas | Fila com `deque` na busca em largura e no posicionamento do grafo. Uma lista encadeada artesanal não traz benefício aqui. O exercício de implementar nós continua sendo uma atividade própria. |
| S3_04 | Complexidade assintótica | Custos e limites da busca, caminhos, matrizes e ordenação explicados abaixo. O bloco repetido não corresponde a uma segunda funcionalidade. |
| S3_05 | Busca linear/binária e ordenações elementares | Identidades usam consultas SQL; associações internas usam dicionários; prioridades usam `sort`. Busca binária exige dados ordenados e não resolve autocomplete textual. Bubble, selection e insertion sort ficam na prática comparativa, sem substituir o sort nativo. |
| S3_06 | Coesão, acoplamento, PEP 8 e qualidade | Domínio puro, matemática, aplicação e adaptadores separados. Pequenos laços explícitos substituem compreensões usadas só para imprimir. Não foi acrescentado um formatador ou declarado um selo global de lint sem execução. |
| S3_07 | Testes unitários e integração | Verificação isolada de algoritmos, oráculos matemáticos, permissões, persistência e navegador; resultados em `VALIDACAO.md`. As suítes temporárias ficam fora da distribuição conforme a organização solicitada anteriormente. Não foi produzida uma porcentagem nova de cobertura. |
| S3_08 | Git, branches, revisão e CI | É uma exigência de processo: este ZIP não comprova branches, merges, revisão ou execução em CI. Eles devem existir no repositório verdadeiro. Não foi fabricado um histórico de etapas a partir de um projeto pronto. |
| S3_09 | Transformações, núcleo, imagem, posto e composição | Novo diagnóstico de M: domínio/codomínio, posto numérico, nulidade e colunas nulas. A composição de exposição e incidência é explicada abaixo. Não se calcula uma base inteira do núcleo na interface. |
| S3_10 | Sistemas lineares e eliminação | Modelo existente `(I-A)x=b`, resolvido com `numpy.linalg.solve`. Nova decomposição da equação de cada ativo. A implementação manual de Gauss continua útil como exercício e conferência pequena. |
| S3_11 | Determinante, inversa, dominância diagonal | Validador existente verifica estabilidade, determinante relativo, posto e condição. A solução usa solve. Sarrus serve apenas para 3×3, e não é uma solução geral para o inventário. |
| S3_12 | Ponto flutuante, tolerância e condicionamento | Novo resíduo absoluto e normalizado antes de arredondar x. Condição e limites existentes são preservados. Resíduo e condição têm interpretações diferentes. |
| S3_13 | Lógica proposicional | Aparece nas regras de permissão, inclusão de status em M e condições do recomendador. Tabelas-verdade podem demonstrar essas regras, sem um novo editor lógico no produto. |
| S3_14 | Portas lógicas e arquitetura de computadores | Fundamentação conceitual. Não há necessidade de implementar circuitos ou simular uma CPU no inventário. |
| S3_15 | UX, heurísticas e acessibilidade | Novos formulários rotulados, erros claros, explicações, tabelas com legenda e detalhes opcionais. Navegação por teclado e verificações de acessibilidade se somam às já existentes. Isso não certifica integralmente WCAG. |
| S3_16 | CSS Grid, variáveis e arrays JS | O CSS e a apresentação responsiva existentes são reaproveitados. Arrays do grafo e componentes atuais continuam funcionais, sem biblioteca visual adicional. |
| S3_17 | Promises, async/await, fetch e JSON | Integrações CVE e APIs do site já usam esses mecanismos. Os novos formulários de leitura funcionam também sem JavaScript próprio. Não faz sentido acrescentar fetch a toda navegação. |
| S3_18 | REST, HTTP e endpoints | Duas consultas GET novas com respostas JSON e permissões. Não representam uma API REST completa de escrita: CRUD atual usa formulários e serviços. Sessão ausente redireciona ao login; permissão insuficiente retorna 403. |
| S3_19 | Framework Python, SQL, CRUD e modelo relacional | Mantido Django/ORM/SQLite já integrado ao domínio puro. Não foi acrescentado Flask ou FastAPI em paralelo. O relacionamento N:M continua explícito em Incidencia. |
| S3_20 | Redes, autenticação/autorização, privacidade, estatística e sustentabilidade | IPv4, serviços, autenticação, permissões e proteção de arquivos já têm usos concretos. São fundamentos para a defesa, sem alegar conformidade automática com LGPD ou estatísticas/telemetria que não foram coletadas. |

**Produto funcional e entregáveis acadêmicos não são equivalentes.** As atividades
que pedem comparação cronometrada de algoritmos, implementações manuais, tabelas-
verdade, relatório de cobertura ou prova de CI exigem suas próprias evidências.
O guia não apresenta esses trabalhos como concluídos por analogia.

## 1. Dependentes: de uma conexão direta ao alcance completo

### Problema e evolução

Antes, a matriz já continha os vínculos e o desenho destacava dependentes entre os
nós exibidos. O desenho tem janela de até 60 ativos. Agora existe uma consulta no
servidor que percorre **todo o inventário**, conta todos os dependentes alcançados
e apresenta até 50 caminhos no terminal/site. A API aceita limite de 1 a 200
caminhos; limitar a saída não interrompe a contagem.

Pense numa rede de abastecimento: se a estação de tratamento parar, queremos saber
quais bairros recebem sua água, inclusive passando por reservatórios intermediários.
Não basta listar apenas os canos diretamente conectados à estação.

O cadastro `A[i,j]` significa que i depende de j. Portanto, para investigar a
repercussão de um problema em j, o grafo percorre **fornecedor → dependente**.
No cenário didático: Switch → Banco → App → Web. A seta pode parecer inversa à
frase “Web depende de App”; o sentido é o da propagação do efeito.

### Funções e decisões

- `GrafoDependencias.__init__`: recebe códigos e relações puras; constrói a lista
  de adjacência. Rejeita referências desconhecidas, códigos repetidos, autorrelação
  e pesos inválidos. Só peso positivo cria uma aresta de alcance.
- `GrafoDependencias.alcance`: usa busca em largura (BFS). Coloca a origem numa fila,
  retira com `popleft`, visita os vizinhos ainda não vistos e os coloca no fim.
  O dicionário de predecessores registra a visita e permite reconstruir caminhos.
  Assim, um ciclo não faz o algoritmo rodar para sempre nem recontar a origem.
- `analisar_impacto`: confere as duas permissões, consulta a identidade do ativo,
  carrega o grafo e acrescenta hostnames/IDs numéricos à resposta. A matemática
  do risco não é necessária para essa consulta estrutural.
- `api_impacto`, a página do mapa e `impacto_dependencias` são adaptadores. Reutilizam
  o serviço, sem implementar três algoritmos diferentes.

A fila FIFO é como uma fila de atendimento: quem entrou primeiro sai primeiro.
Isso visita todos os vizinhos a um salto antes dos que estão a dois. O caminho
apresentado tem o **menor número de saltos**; pesos não são usados para escolher
esse caminho. Ele não é necessariamente o mais arriscado, rápido ou provável.

A BFS custa O(V+E), com O(V) de memória para visitas, distâncias e predecessores.
Construir a adjacência também custa O(V+E). Reconstruir os caminhos apresentados
acrescenta a soma de seus comprimentos. Em uma cadeia longa, imprimir todos os
caminhos pode ser caro, mesmo com uma busca linear. Esse é o motivo do limite.

Não usamos lista com `pop(0)`, que desloca os elementos, nem recursão por ativo,
que acumularia chamadas. `deque` já oferece a operação de fila adequada.

**Não equivale a um scanner:** o alcance reflete apenas vínculos cadastrados.
Ausência de caminho não comprova isolamento físico; presença de caminho não
confirma exploração ou comprometimento. Peso zero não é conexão de propagação.

## 2. Entender M: transformar severidades em risco próprio

Com n ativos e m vulnerabilidades, `M` tem n linhas e m colunas:

```text
M: R^m → R^n
v: m severidades
b = Mv: n riscos próprios
```

Uma analogia é uma receita: cada coluna identifica um ingrediente (vulnerabilidade)
e cada linha mostra quais ingredientes entram em um prato (ativo). Uma mesma
vulnerabilidade pode entrar no risco de vários ativos: é a relação N:M.

No perfil puro, `M[i,j]=1` quando há uma incidência em estado considerado e
`b[i]` soma seus CVSS. SUGERIDA, MITIGADA e CORRIGIDA não entram nessa soma.
No operacional, a exposição e o acréscimo KEV modificam o cálculo; ambos os perfis
ficam identificados na tela. O CVSS técnico original continua disponível.

### Posto, imagem e núcleo sem confundir os significados

O posto é a dimensão da imagem: quantas direções independentes M pode produzir.
A nulidade é `m − posto`, pela relação posto-nulidade. O núcleo contém variações
Δv com `MΔv=0`, que não mudam o risco próprio no modelo linear.

Exemplo pedagógico, separado do seed:

```text
M = [[1, 0, 0, 1],
     [0, 1, 0, 0],
     [0, 0, 0, 0]]
v = [1, 2, 3, 4]
b = [5, 2, 0]
```

O posto é 2 e a nulidade é 4−2=2. A terceira coluna é zero: aquela vulnerabilidade
não tem incidência considerada. A primeira e a quarta colunas são iguais:
a variação `Δv=[−1,0,0,1]` mantém b porque uma parcela compensa a outra.
Isso **não** significa que duas CVEs sejam inofensivas. O núcleo admite componentes
negativas e a interpretação deve respeitar os limites reais de CVSS e os cadastros.
Uma coluna nula também pode decorrer de ausência de confirmação, sem provar que a
vulnerabilidade não existe na empresa.

O posto usa `numpy.linalg.matrix_rank`, por decomposição em valores singulares com
tolerância numérica padrão. Não é um cálculo simbólico exato. É apresentado apenas
até 200 linhas e 200 colunas para limitar o custo adicional; esse limite não torna
o motor de risco inteiro adequado a grandes inventários.

### Composição das transformações

Se F for a matriz diagonal de exposição, então `F(Mv)=(FM)v`. Multiplicar depois
o risco próprio de cada ativo pelo seu fator equivale a ponderar antes as linhas
de M. No perfil operacional, v é substituído pela severidade ajustada por KEV.
Essa é uma aplicação real de composição, sem precisar criar um menu genérico de
multiplicação de matrizes desconectado do inventário.

`DiagnosticoLinear.analisar` lê o resultado do mesmo modelo, determina dimensões,
posto/nulidade, colunas nulas e a equação selecionada. `explicar_modelo` confere as
quatro permissões de risco, seleciona o ativo e coordena o diagnóstico. A view de
matrizes reutiliza o resultado na mesma transação, mantendo a explicação coerente
com o resultado exibido.

## 3. Conferir x: resíduo e condicionamento

Se `B=I−A`, a solução desejada satisfaz `Bx=b`. A função `residuos` calcula:

```text
r = Bx − b
resíduo absoluto = ||r||∞
resíduo normalizado = ||r||∞ / (||B||∞ ||x||∞ + ||b||∞)
```

Para um vetor, a norma infinito é o maior valor absoluto; para a matriz é a maior
soma absoluta de uma linha. A versão normalizada compara o erro com a escala do
problema. Quando tudo é zero, adota-se resíduo normalizado zero. O denominador é
reescalado no código para evitar formar diretamente um produto muito grande.
Valores não finitos produzem erro explícito, não uma falsa conferência aprovada.

O motor calcula os resíduos **antes de arredondar** b/x para apresentação. A tela
usa notação científica para não transformar um valor pequeno em um enganoso `0,00`.
As parcelas da equação são para leitura e usam números já apresentados/arredondados;
pequenas diferenças ao somá-las à mão podem ser apenas arredondamento.

Um resíduo pequeno é como conferir que o troco fecha: a aritmética está coerente.
O número de condição é outra pergunta: quanto a resposta pode mudar se os dados de
entrada mudarem um pouco? Um sistema mal condicionado pode ter resíduo pequeno e
resposta muito sensível. Nenhuma dessas verificações confirma a qualidade do
cadastro, prevê ataques ou valida empiricamente os pesos Aij.

O `solve` continua obtendo x. Não foi substituído por `inv(B) @ b`. A checagem existente
de estabilidade e condição permanece. O cache recebeu uma versão de formato para
que resultados antigos sem resíduos sejam recalculados automaticamente.

### Conferência manual com o cenário de quatro ativos

| Ativo | Risco próprio b | Parcela recebida | Risco efetivo x |
|---|---:|---|---:|
| Switch | 5,00 | nenhuma | 5,00 |
| Banco | 12,50 | 0,3 × 5,00 = 1,50 | 14,00 |
| App | 17,30 | 0,6 × 14,00 = 8,40 | 25,70 |
| Web | 9,80 | 0,5 × 25,70 = 12,85 | 22,65 |

Total: 67,35. A explicação do Web deve mostrar `9,80 + 12,85 = 22,65`.
As notas são didáticas e não são associadas a CVEs públicas no seed novo. A busca
NVD continua independente e verdadeira quando a consulta externa é solicitada.

## 4. Polimorfismo visível e reconstrução dos objetos

A classe base já se chama `Equipamento`. Ela exerce o papel de `Ativo` pedido no
exercício, enquanto `models.Ativo` é o adaptador SQL. Criar outra base com o mesmo
papel só para trocar o nome aumentaria a ambiguidade. Se o docente exigir a grafia
literal `Ativo` na classe de domínio, combine a nomenclatura; não são duas bases
concorrentes no código entregue.

Antes, as subclasses já diferiam no fator de exposição, mas herdavam a mesma
implementação de detalhes. Agora:

- `Servidor.exibir_detalhes` chama `super` e acrescenta sistema/versão;
- `Notebook.exibir_detalhes` acrescenta o responsável pela custódia;
- `Roteador.administracao_remota` concentra a regra já usada no fator de exposição;
- `Roteador.exibir_detalhes` informa se o cadastro indica administração remota.

O fator do roteador continua sendo o mesmo. Uma porta cadastrada não é resultado
de uma varredura ativa. `super` reaproveita a parte comum antes de especializar a
resposta: como uma ficha padrão com uma seção própria para cada equipamento.

O serviço percorre até 12 objetos reais e faz as mesmas chamadas em cada um:

```python
for equipamento in equipamentos:
    equipamento.exibir_detalhes()
    equipamento.fator_exposicao()
    isinstance(equipamento, Equipamento)
```

As duas primeiras chamadas demonstram polimorfismo. `isinstance` verifica a relação
de tipo; não escolhe qual método chamar. `Equipamento.from_dict` usa o campo `tipo`
para recuperar a subclasse registrada e preserva código, número e `sala_id`.
Incidências e dependências permanecem arrays separados com os mesmos códigos de
referência. Reconstruir objetos em memória não importa automaticamente dados no SQL.

### Conferir a recarga sem alterar o SQL

Depois de exportar pelo menu 10, opção 2, abra o shell do projeto:

```powershell
& ".\.venv\Scripts\python.exe" manage.py shell
```

Cole este exemplo. Ele lê os quatro arquivos exportados e reconstrói objetos em
memória; não grava o banco. Para que a lista mostre Notebook e Roteador, esses
subtipos precisam ter sido cadastrados antes da exportação.

```python
from django.conf import settings
from inventario.infraestrutura.repositorio_json import RepositorioJSON
from inventario.dominio.equipamentos import Equipamento
from inventario.dominio.vulnerabilidades import Vulnerabilidade, Incidencia, Dependencia

dados = settings.DATA_DIR
ler = lambda nome: RepositorioJSON(dados / nome).listar()
registros = ler("equipamentos.json")
equipamentos = [Equipamento.from_dict(item) for item in registros]
falhas = [Vulnerabilidade.from_dict(item) for item in ler("vulnerabilidades.json")]
vinculos = [Incidencia(**item) for item in ler("incidencias.json")]
dependencias = [Dependencia(**item) for item in ler("dependencias.json")]
ids = {obj.id for obj in equipamentos}
ids_falhas = {obj.id for obj in falhas}

assert [(obj.id, obj.id_numerico, obj.sala_id) for obj in equipamentos] == [
    (item["id"], item.get("id_numerico"), item.get("sala_id")) for item in registros
]
assert all(v.equipamento_id in ids and v.vulnerabilidade_id in ids_falhas for v in vinculos)
assert all(d.dependente_id in ids and d.fornecedor_id in ids for d in dependencias)
for obj in equipamentos:
    print(type(obj).__name__, isinstance(obj, Equipamento), obj.exibir_detalhes())
print("IDs preservados e referências reconstruídas:", len(vinculos), len(dependencias))
```

Aqui a expressão lambda só abrevia a leitura repetida de um arquivo. Em um caso de
uso maior, uma função nomeada facilitaria documentação e tratamento de erros. O
exemplo não pretende validar a existência física das salas: `sala_id` é preservado,
mas o conjunto completo de salas pertence ao banco SQL e ao backup correspondente.

## 5. Onde usar os acréscimos

Prepare a instalação conforme o README, entre com um usuário autorizado e use seus
próprios ativos. Para o cenário didático, carregue a opção demonstrativa do menu 11
**apenas numa base de demonstração vazia**, nunca sobre sua base de trabalho.

| Canal | Operação |
|---|---|
| Terminal | `5 → 5`: dependentes diretos/indiretos; informe número, código ou hostname do fornecedor |
| Terminal | `6 → 9`: conferir M e a equação; vazio seleciona o primeiro ativo; escolha puro/operacional |
| Site | **Mapa → Dependentes diretos e indiretos**; consulte o fornecedor |
| Site | **Matrizes → Conferir a solução e entender M**; selecione o ativo e abra os detalhes |
| API | `GET /api/impacto/?ativo=4H00001&limite=50` |
| API | `GET /api/risco/diagnostico/?ativo=7N00001&perfil=puro` |

Os códigos dos exemplos pertencem ao seed; use os seus em uma instalação real.
No navegador autenticado, as URLs API podem ser abertas diretamente. Impacto exige
`view_ativo` e `view_dependencia`. Diagnóstico exige também `view_vulnerabilidade` e
`view_incidencia`. As páginas completas de mapa/matrizes mantêm as permissões do
cálculo de risco. GET não altera cadastros nem cria incidências/auditoria de cadastro;
caches de cálculo podem ser atualizados internamente.

A API de impacto usa 400 para entrada inválida, 404 para ativo inexistente e 405
para método indevido. A de diagnóstico usa 422 para perfil/validação matemática,
404 para ativo inexistente e 405 para método indevido. Usuário sem sessão recebe
redirecionamento ao login e usuário sem permissão, 403. Não são endpoints públicos.

## 6. Trabalho 2: o que continua prioritário

| Requisito | Situação e evidência necessária |
|---|---|
| Equipamentos orientados a objetos — 20% | Hierarquia de domínio, métodos especializados, polimorfismo e reconstrução. Demonstre objetos reais de mais de um subtipo. |
| Array de objetos JSON — 20% | Exportação existente do menu 10; confira o campo tipo, IDs e relações na recarga. O SQL não elimina a entrega JSON. |
| Docker em execução por 24 horas — 45% | Dockerfile/Compose, persistência e healthcheck estão preparados. É indispensável executar no ambiente solicitado e coletar evidência real; este ZIP não prova 24 horas. |
| Álgebra linear — 15% | M, v, A, validação de I−A e solve existentes; diagnóstico melhora a explicação, sem substituir os requisitos. |
| Requisitos herdados | CRUD, Enum, ID numérico, ramas/merges e demais itens da ementa continuam sujeitos à avaliação e às evidências do repositório. |

A prioridade de avaliação continua sendo a execução de 24 horas, que vale mais do
que qualquer recurso adicional. Não há Docker disponível no ambiente desta revisão.
Não se declara esse requisito concluído com base apenas nos arquivos de configuração.

## 7. Demonstração curta para a defesa

1. Mostre dois subtipos no inventário e abra os detalhes de polimorfismo. Explique
   o que é comum e o que foi especializado, sem começar por metaprogramação.
2. Exporte JSON pelo menu 10 e mostre tipo, código, ID numérico e vínculos. Explique
   a reconstrução por fábrica e a diferença entre recarga em memória e importação SQL.
3. No mapa, consulte o switch: o caminho até o Web tem três saltos. Explique fila,
   visitas e diferença entre alcance estrutural e risco ponderado.
4. Nas matrizes, selecione o Web: mostre b, a parcela 0,5 × 25,7 e x=22,65. Abra o
   resíduo; explique que ele confere a equação, não a realidade física.
5. Termine com as evidências operacionais reais: persistência após reinício, saúde
   e disponibilidade em Docker. Se ainda não tiver a coleta de 24 horas, diga isso.

Perguntas úteis para ensaiar: por que não recursão? Por que solve? Uma coluna nula
prova segurança? Nulidade conta CVEs descartáveis? Uma consulta NVD detecta falhas
no meu servidor? Um caminho mais curto é o de maior risco? As respostas estão
ligadas às distinções acima, sem depender de termos decorados.

## Referências técnicas verificáveis

- Material fornecido: `Documento sem título.md`, tópicos S3_01 a S3_20.
- Requisitos fornecidos: `Trabalho_2.pdf`.
- Python, `collections.deque`: https://docs.python.org/3/library/collections.html#collections.deque
- NumPy, posto numérico e tolerância: https://numpy.org/doc/stable/reference/generated/numpy.linalg.matrix_rank.html

Os livros e vídeos listados no material não foram usados como se tivessem sido
integralmente lidos nesta revisão. O comportamento descrito acima é o do código
entregue; os resultados efetivamente conferidos estão em `VALIDACAO.md`.
