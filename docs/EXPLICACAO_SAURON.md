# Explicação técnica — Sauron consolidado

Esta defesa descreve a implementação atual. Consulte ARQUITETURA.md para localizar os módulos.

## 1. Evolução arquitetural

Na versão original, cada ativo era um dicionário e cada vulnerabilidade ficava aninhada dentro dele. Essa organização era adequada ao primeiro estágio didático: permitia praticar dicionários, CRUD, validação e persistência. Porém, ela impunha duas limitações.

Primeiro, um dicionário guarda dados, mas não estabelece um contrato de comportamento. Segundo, a mesma vulnerabilidade precisava ser repetida em cada ativo afetado. A nova solução transforma os substantivos do domínio em objetos e as relações em entidades explícitas.

Uma analogia útil é a diferença entre uma ficha preenchida e um profissional. A ficha contém informações; o profissional também sabe agir. `Equipamento` contém identidade, fabricante e localização, mas também estabelece operações como `fator_exposicao()` e `exibir_detalhes()`.

## 2. Herança e polimorfismo

`Equipamento` é abstrata: não faz sentido cadastrar um “equipamento genérico” quando o tipo determina regras reais. `Servidor`, `Switch`, `Notebook` e as demais subclasses fornecem implementações próprias.

Ao percorrer uma lista heterogênea, o chamador usa a mesma operação:

```python
for equipamento in equipamentos:
    print(equipamento.exibir_detalhes())
    print(equipamento.fator_exposicao())
```

O laço não precisa perguntar qual é o tipo. Cada objeto responde segundo sua classe. Isso é polimorfismo: uma mensagem comum, comportamentos específicos.

Na reconstrução do JSON, uma fábrica explícita relaciona o campo `tipo` à classe. A solução evita um encadeamento de `if/elif`, mas continua simples o bastante para ser defendida diante da banca.

## 3. Identidade controlada

Um ID como `4H21444` contém informação estrutural:

- `4`: Switch;
- `H`: fabricante Huawei;
- `21444`: sequência única.

O hostname é derivado do mesmo cadastro, por exemplo `SAU-SWT-HUAW-21444`. O usuário não digita um número arbitrário e o sistema valida se o primeiro algarismo corresponde ao tipo.

É importante reconhecer a limitação: IDs “inteligentes” acoplam identidade a atributos que podem mudar. Em um sistema empresarial maduro, seria preferível usar uma chave interna imutável e tratar esse código como patrimônio. Para a ementa e para a legibilidade do protótipo, a convenção é intencional e documentada.

## 4. Vulnerabilidade como entidade N:M

O CVE é um registro público; não pertence exclusivamente a um computador. A relação correta é muitos-para-muitos:

- um ativo pode possuir muitas vulnerabilidades;
- uma vulnerabilidade pode afetar muitos ativos.

`Incidencia` é a entidade associativa. Ela guarda o que varia por vínculo: status, data da detecção, versão afetada e observações. Corrigir uma vulnerabilidade em um servidor não apaga o registro dos demais.

O ID interno `VUL-RCE-0001` não substitui `CVE-2021-44228`. O primeiro identifica o achado no Sauron; o segundo identifica publicamente uma vulnerabilidade. Falhas locais de configuração podem não possuir CVE.

## 5. CVSS

O sistema guarda pontuação, versão e vetor. “Crítica” é uma visualização derivada de `9,0 ≤ CVSS ≤ 10,0`, não a fonte primária do cálculo.

No CVSS Base 3.1:

```text
ISS = 1 - (1-C)(1-I)(1-A)
Explorabilidade = 8,22 × AV × AC × PR × UI
```

A implementação valida todas as métricas obrigatórias, considera a mudança de escopo e usa arredondamento sempre para cima em uma casa decimal. O teste baseado no exemplo oficial verifica que o vetor `CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N` resulta em 6,1.

## 6. Modelo de risco

`M` registra a incidência, `v` as severidades e `A` a transmissão pelas dependências.

```text
b = Mv
x = b + Ax
(I-A)x = b
```

O programa usa fatoração LU esparsa do SciPy (`splu`) para resolver o sistema, sem calcular a inversa para obter `x`. A inversa é uma representação matemática útil, mas resolver o sistema diretamente evita materializá-la.

Antes da solução são verificados:

- `0 ≤ Aij < 1`;
- diagonal de `A` igual a zero;
- raio espectral de `A` menor que 1;
- para até 300 ativos, ou quando o diagnóstico é solicitado, número de condição finito e abaixo do limite de instabilidade. Para matrizes maiores o cálculo automático de condição é omitido.

A soma de cada linha menor que um é uma condição suficiente para convergência, não necessária. Por isso, a validação numérica permanece mesmo quando a interface restringe o cadastro.

## 7. Sensibilidade e série de Neumann

A derivada do risco efetivo em relação ao vetor de vulnerabilidades é obtida resolvendo:

```text
(I-A)S = M
```

Cada coluna de `S` mostra como uma unidade de CVSS se propaga pela infraestrutura. Ao multiplicar a coluna pelo CVSS atual, estima-se o ganho obtido ao eliminar a vulnerabilidade. Isso separa “gravidade isolada” de “impacto estrutural”.

Quando o raio espectral é menor que um:

```text
x = b + Ab + A²b + ...
```

Cada termo é um salto de contágio. No cenário triangular da demonstração, `A⁴=0`; logo a série termina exatamente depois de três saltos.

## 8. Modo Euler

O antigo módulo misturava entrada, saída e cálculo. Agora:

- `FuncaoMatematica` interpreta somente uma árvore sintática permitida;
- `Derivador` aplica diferenças centrais;
- `Integrador` aplica Simpson ou trapézios;
- Django apenas coleta parâmetros e exibe o resultado.

Não é utilizado `eval`: o programa interpreta diretamente uma árvore sintática restrita e aceita apenas nós, operações e funções explicitamente previstos.

## 9. Persistência e adaptadores

O domínio não conhece Django. O ORM transforma linhas SQL em objetos do domínio; o repositório JSON oferece outra persistência. Essa separação permite cumprir a entrega em JSON e, simultaneamente, experimentar SQLite.

O comando legado `exportar_json --saida DIRETORIO` produz listas de objetos por solicitação explícita. IDs preservam os vínculos entre equipamentos, vulnerabilidades, incidências e dependências.

## 10. Segurança e auditoria

Django fornece autenticação, grupos e permissões. O cenário cria Operadores e Gerentes. A alocação de um ativo em sala incompatível exige autorização, justificativa e usuário autorizador.

Os registros de auditoria não aceitam alteração nem exclusão pela aplicação ou pelo painel administrativo. Em produção, imutabilidade absoluta exigiria controles adicionais no banco, retenção externa e encadeamento criptográfico; a solução atual é uma garantia na camada de aplicação.

## 11. Contêiner

O menu interativo não é o processo principal. O contêiner executa Gunicorn continuamente, responde em `/api/saude/`, persiste SQLite e JSON em volume e reinicia automaticamente. Ele roda como usuário não-root.

Para a evidência de 24 horas, devem ser preservados:

- horário inicial;
- saída de `docker compose ps`;
- estado do healthcheck;
- logs do período;
- dados antes e depois de um reinício.

## 12. Sistema imune de vulnerabilidades

O recomendador opera sobre características dos ativos e vulnerabilidades já cadastradas.
Ele utiliza vetores, afinidade de cosseno, confirmação ou rejeição humana, reforço e decaimento
exponencial. Persistem anticorpos, sugestões e tolerâncias no banco. Uma sugestão não equivale
a malware detectado nem autoriza correção automática. O comportamento está em
`inventario/aplicacao/imune.py`; as classes puras estão em `inventario/dominio/sistema_imune.py`.

## 13. Autocomplete e consulta externa

`dominio/autocomplete.py` normaliza acentos, espaços e identificadores. A classificação prioriza
identidade exata, prefixo, palavras presentes e uma pequena distância de edição de Levenshtein.
O algoritmo só sugere registros fornecidos pelo inventário, pelo KEV ou pelo cache NVD.
Uma entrada normalizada, como `2021 44228`, representa um possível identificador; sua existência
é verificada na consulta externa. O apelido conhecido Log4Shell auxilia a busca de sua CVE.

A digitação não produz uma chamada externa por tecla: há espera de 250 ms, cancelamento de
requisições antigas e seleção explícita. Isso mantém a resposta rápida e respeita os limites
compartilhados da NVD. O botão de consulta envia um POST com CSRF ao Django, que acessa a
API oficial por identificador ou `keywordSearch`. A interface mostra fonte, data, vetor e pontuação.
A matemática recalcula a base CVSS 3.1 e compara com o resultado recebido; outras versões
são identificadas como pontuação da fonte, sem alegação de recálculo.

A analogia é um catálogo de biblioteca: completar o título ajuda a encontrar o livro correto,
mas encontrar o livro não prova que ele esteja na sua estante. Da mesma forma, encontrar
uma CVE não confirma que um ativo esteja vulnerável. O vínculo exige revisão de produto,
versão, configuração e evidência; sugestões por CPE permanecem sugestões até a confirmação.

## 14. Interfaces e instalação

Terminal e navegador usam os mesmos serviços de cadastro, risco e auditoria. As páginas
ficam em `inventario/web`, os templates em `inventario/templates` e CSS/JS em `inventario/static`.
A matemática está concentrada em `inventario/matematica`, sem imports Django, input ou print.

Com DEBUG=0, o manifesto de estáticos deve existir antes de servir páginas. O comando
`preparar_servidor` aplica migrações, prepara permissões, executa collectstatic e verifica a
instalação. O menu 11 também prepara o ambiente antes de abrir a interface web. O comando
`diagnosticar` informa quais componentes não estão prontos, sem expor a chave privada.

Entradas matemáticas inválidas são erros de uso e recebem explicação na própria página.
Falhas operacionais conhecidas retornam 503; erros inesperados mantêm 500, são registrados
nos logs e recebem um código de requisição. Não se transforma uma falha em sucesso artificial.

## 15. Identidade inteira e operação pela ficha

Cada ativo passa a ter `id_numerico`, inteiro positivo e único. O contador SQL fica
na mesma transação do cadastro, sob a trava de escrita. Excluir o último registro
não diminui o contador. Pense em um número de matrícula: um estudante sair não
transfere automaticamente sua matrícula para o próximo. O código como `4H21444`
continua indicando tipo/fabricante e preservando as referências antigas.

A migração atribui os números aos ativos existentes sem trocar suas chaves antigas.
O JSON guarda ambos; a conversão para a classe concreta recupera também a identidade
numérica. O método `consultar_ativo` centraliza a leitura por número, código, hostname
ou nome exato e rejeita ambiguidades. O Enum de categorias disponibiliza `.codigo`
inteiro, preservando `.value` textual no armazenamento legado.

Na ficha, os formulários de vínculo e de fornecedor já conhecem o ativo. A URL fixa
essa escolha e o servidor ignora tentativas de transferi-la por um campo POST adulterado.
Uma busca NVD pode levar à revisão e ao cadastro conjunto da vulnerabilidade e da
incidência. O serviço `cadastrar_e_vincular` usa uma transação: se o vínculo falhar,
o cadastro e a auditoria daquela operação também são revertidos. É como efetuar uma
transferência bancária: não basta concluir apenas uma das duas gravações.

O estado inicial é SUGERIDA, fora do cálculo. Uma CVE existente é reutilizada, pois
sua descrição é global, mas a situação de correção é individual por incidência.
O serviço não reabre uma incidência corrigida quando o mesmo vínculo é reenviado.
No terminal, o menu 7, opção 6, chama esses mesmos casos de uso.

O cenário matemático novo usa notas didáticas sem atribuí-las a CVEs públicas. O
risco calculado do exemplo continua o mesmo; consulta externa e exercício numérico
têm origens e finalidades diferentes. Bases antigas são preservadas e exibem sua fonte.

## 16. Limites da defesa

CVSS mede severidade técnica e não probabilidade de ataque nem risco empresarial completo.
As matrizes M e A representam o inventário confirmado e as dependências informadas; a NVD não
conhece automaticamente a rede da empresa. Não há scanner de endpoints nesta entrega.
SQLite é adequado ao protótipo e serializa os escritores; maior escala exige reavaliar o banco.
A auditoria em cadeia detecta alteração, mas não resiste a um administrador que reescreva
banco e hashes; imutabilidade forte exige armazenamento externo protegido.

A validação local com Gunicorn e navegador não substitui os testes no servidor de destino,
o certificado HTTPS, as permissões do volume e a coleta real de 24 horas em Docker.

## 17. Conteúdos adicionais com função concreta

O alcance completo das dependências usa `GrafoDependencias`, uma lista de adjacência
e BFS com `deque`. O predecessor serve simultaneamente para reconhecer visitas e
reconstruir um caminho com o menor número de saltos. A visitação custa O(V+E), além
do custo de reconstruir os caminhos apresentados. Os ciclos terminam, e a origem
não é contada como dependente de si mesma. Pesos positivos definem alcançabilidade;
seu valor não é uma distância nem uma probabilidade de ataque.

O diagnóstico matricial mostra a transformação M: R^m → R^n, posto e nulidade.
O núcleo representa variações de severidade que M não distingue, inclusive com
componentes negativas; não é uma lista de CVEs seguras. Posto/nulidade adicionais
ficam limitados a 200 linhas/colunas, sem prometer escalabilidade do solver inteiro.

O motor calcula ||(I−A)x−b||∞ e sua normalização antes de arredondar os resultados.
A decomposição por ativo permite explicar risco próprio, exposição e parcelas dos
fornecedores. Resíduo confere consistência aritmética; condicionamento informa
sensibilidade; nenhum dos dois certifica a qualidade do cadastro.

`Servidor`, `Notebook` e `Roteador` agora sobrescrevem `exibir_detalhes` com `super`.
A demonstração usa objetos cadastrados, sem criar dados artificiais ou decidir o
método com uma cadeia de `isinstance`. A reconstrução pelo campo tipo e os IDs
continuam compatíveis. O detalhamento de cada função nova, analogias, exemplo
manual, matriz de conteúdos e roteiro de apresentação estão em
[CONTEUDOS_APLICADOS.md](CONTEUDOS_APLICADOS.md).
