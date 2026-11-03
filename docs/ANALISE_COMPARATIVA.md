# Comparação crítica e decisões implementadas

Análise do arquivo `Inventario-Ativos-TI-main.zip` enviado em 15/10/2026,
comparado à distribuição consolidada do Sauron e às duas avaliações fornecidas.
O código recebido foi inspecionado; seu motor matemático foi exercitado com objetos
controlados. A aplicação recebida inteira não foi instalada nem publicada. As
validações de execução descritas em VALIDACAO.md referem-se ao Sauron.

## Juízo técnico

A melhor contribuição do projeto recebido é a navegação centrada no equipamento:
identidade, vulnerabilidades e dependências no mesmo contexto. O frontend comunica
bem essa intenção. Contudo, parte importante da experiência visual não está ligada
a operações persistidas. A aparência de uma operação concluída precisa ser
confirmada pelo servidor e por uma leitura posterior do banco.

O Sauron já possui mapa, matrizes, consulta externa, relações N:M e análise de risco
mais completa. Reescrever tudo em React acrescentaria uma segunda aplicação, um
contrato de API, um build e outra cadeia de dependências sem resolver um requisito
pendente. Foram aproveitadas ideias de interação, com implementação própria nas
camadas já existentes; não foram copiados componentes ou a arquitetura do colega.

## Achados no projeto recebido

| Prioridade | Evidência no código | Consequência |
|---|---|---|
| Crítica | `frontend/src/services/api.ts`: as falhas de `fetchAssets` e `fetchDashboardMetrics` retornam `initialAssets`/`initialMetrics` | Um backend fora do ar pode ser apresentado como um inventário preenchido e saudável. Um modo demonstrativo precisa ser explícito, nunca fallback silencioso de produção. |
| Crítica | `linkCveToAssetOnServer` e `addConnectionOnServer` montam resultados locais no `catch`; exclusões ignoram falhas | O navegador pode mostrar sucesso sem gravar, e os dados reaparecem ao recarregar. |
| Crítica | `App.handleAddAsset` somente executa `setAssets`; `handleAddAsset` não chama criação no backend | O cadastro visual não comprova o CRUD persistido. |
| Crítica | `motor_matematico.py` usa `matriz_A[i][j] = 1` | Contraria `Aij ∈ [0,1)` da ementa; o peso escolhido no frontend não existe na relação SQL do backend. |
| Alta | `Equipamento.id_ativo` não é `unique`, mas é a chave de `id_para_indice` | IDs repetidos sobrescrevem posições no dicionário usado pelo cálculo. A PK automática do Django não corrige a ambiguidade desse segundo identificador. |
| Alta | O cálculo retorna `None` quando encontra singularidade; a view redireciona sem tratar esse retorno | Resultados antigos continuam gravados e podem parecer atuais. Falta condicionalidade numérica e retorno explícito de falha. |
| Alta | `CVEService` só lê o primeiro CVSS 3.1, converte ausência em `0.0`, usa `requests.get` sem timeout | Sem avaliação pode parecer sem gravidade; a chamada pode ocupar um worker por tempo indeterminado. Também não há atualização de uma CVE já existente pelo `get_or_create`. |
| Alta | APIs DRF não definem política obrigatória de permissões; operações HTML não verificam usuário/permissão e algumas exclusões aceitam GET | A presença do middleware de autenticação não impõe autorização. No padrão do DRF, ausência de política mantém `AllowAny`. CORS aberto tampouco substitui autenticação. |
| Alta | `Dockerfile` executa `main.py`, ausente no ZIP; `requirements.txt` não lista Django, DRF e extensões importadas | O pacote enviado não demonstra uma instalação reproduzível nem atende por si só à execução contínua. |
| Alta | `ConnectTerminalModal` produz logs fixos de autenticação, isolamento e varredura; `testConnectionPing` inventa latência no erro | São demonstrações visuais. Não evidenciam SSH, ICMP, nmap ou isolamento de rede reais. |
| Média | Rotas chamadas como `/assets/.../cves/`, `/assets/.../connections/` e `/metrics/` não são implementadas nas URLs fornecidas | Os contratos entre frontend e backend estão incompletos. O campo de URL da interface altera texto de estado, mas não reconfigura a instância Axios criada no módulo. |
| Média | Uma mesma CVE aparece com descrições e pontuações diferentes nos arrays do frontend e na lista de vínculo | Não há uma entidade canônica nessas demonstrações; não se deve importar essas listas como base confiável. |
| Média | `initialMetrics.eigenvectorCentrality.matrixA` tem quatro linhas e cinco colunas; seu vetor possui três posições | Esses placeholders não descrevem o produto `Ax` exibido. O sistema linear de risco não deve ser confundido com centralidade por autovetor. |
| Média | `Readme` anuncia módulos e um ponto de entrada ausentes, apesar de avisar que está desatualizado | Falta um roteiro atual de instalação e de demonstração. O arquivo `tests.py` é apenas o esqueleto gerado. |

Exercício independente: com riscos próprios `[5,10]`, o motor original transmite
100% e calcula `[15,10]`. Com a dependência pretendida de 0,5, a solução é `[10,10]`.
Ao acrescentar a dependência reversa, o motor retorna `None` e conserva os valores
anteriores. Isso foi verificado executando a classe original com uma coleção
controlada; não se trata de uma conclusão baseada apenas na aparência do gráfico.

Há decisões úteis: a relação N:M, o uso de `numpy.linalg.solve`, a indexação por
dicionário e a tentativa de separar integração CVE, cálculo e interface. Elas são
boas direções, mas precisam das invariantes e dos contratos descritos acima.

## O que mudou no Sauron

### 1. Identidade inteira e compatibilidade

O requisito da avaliação inicial pede um identificador inteiro único e continua
válido no Trabalho 2. O Sauron anterior só expunha o código alfanumérico solicitado
durante a evolução do projeto. Foi acrescentado `id_numerico`, inteiro positivo,
único no SQL, imutável nas atualizações comuns, pesquisável e exportado em JSON/CSV.

O código como `4H21444` permanece para classificação e compatibilidade. A chave
técnica SQL e as referências antigas continuam usando esse código; o número novo
é uma identidade adicional de inventário, e não uma renomeação disfarçada da PK.
É essa distinção que deve ser explicada na defesa. A ementa exige identificação
inteira, mas não determina o tipo da chave física de cada tabela do SQL.

- `ContadorAtivo` conserva a sequência mesmo quando o último ativo é excluído.
- `reservar_numero` opera na transação e sob a trava de escrita existente. A
  restrição `unique` do SQL permanece como última barreira contra duplicação.
- A migração 0009 numera ativos anteriores sem alterar seus códigos ou vínculos.
- `consultar_ativo` aceita número, código, hostname e nome exato. Nomes ambíguos
  exigem identidade específica; números fora da faixa são tratados como inexistentes.
- `ConversaoAtivo` e `Equipamento` preservam o número na ida/volta do JSON. JSON
  antigo sem o campo ainda pode ser reconstruído; reconstrução não sobrescreve
  automaticamente um objeto já existente no banco.
- Uma restauração explícita pode trazer números preservados, desde que não colidam;
  o contador avança até o maior número restaurado. As interfaces comuns não editam IDs.
- `TipoEquipamento.codigo` fornece um inteiro de 1 a 9 para cada categoria; o
  valor textual de armazenamento do Enum foi preservado para compatibilidade.

### 2. A ficha como ponto de operação

O caminho agora é: **abrir ativo → consultar NVD ou escolher vulnerabilidade →
revisar → gravar → retornar à ficha e ler o estado persistido**.

- `vincular_existente` reutiliza uma vulnerabilidade do catálogo. Um reenvio pelo
  serviço não reabre um vínculo corrigido nem modifica um aceite existente.
- `cadastrar_e_vincular` salva vulnerabilidade, incidência e auditoria na mesma
  transação. Se a segunda gravação falhar, a primeira e seus registros são revertidos.
  A remediação removeu a exportação automática: JSON exige comando explícito e destino.
- O vínculo criado a partir de consulta pública começa como `SUGERIDA`. Uma CVE
  encontrada não comprova que o equipamento está afetado. Só após revisar produto
  e versão o usuário deve confirmar a incidência; sugestões não entram em M.
- O ativo dos formulários contextuais vem da URL autorizada, com campo desabilitado.
  Alterar o valor enviado no POST não transfere o vínculo para outro equipamento.
- A pesquisa mantém o contexto do ativo. Se a CVE já existir, o sistema encaminha
  ao vínculo existente, sem criar outro registro global nem sobrescrever sua nota.
- A ficha permite adicionar fornecedores com peso e sentido explícitos, usando
  a validação já existente de diagonal, faixa dos pesos e soma da linha.
- O terminal recebe **menu 7 → opção 6** para o mesmo caso de uso. Consultar,
  atualizar e vincular também aceitam a identificação numérica.

Os formulários continuam utilizáveis com HTML comum. JavaScript melhora a pesquisa,
mas não representa sozinho a confirmação da gravação.

A verificação no navegador também revelou datas automaticamente renderizadas em
formato brasileiro dentro de `input type="date"`. Esses campos agora recebem
`AAAA-MM-DD`, como o HTML exige, e não bloqueiam o envio por uma data inicial inválida.

### 3. Dados didáticos separados de inteligência externa

Também foi corrigido um problema do Sauron: a nova demonstração deixa de associar
uma CVE pública à nota fictícia de 9,8 escolhida para o exercício. Os valores
`b = [9.8,17.3,12.5,5]` e o total de risco efetivo 67,35 permanecem.

A atualização não apaga nem altera registros antigos do usuário. Se uma base
anterior ainda possuir uma CVE com fonte `Cenário demonstrativo`, a ficha mostra a
origem e o fluxo de vínculo emite orientação para revisar pela NVD. É necessário
revisar esses registros antes de usá-los como inteligência real.

## Atendimento aos requisitos e próximos esforços

| Critério | Situação do Sauron nesta entrega | Evidência ou pendência |
|---|---|---|
| Objetos individuais, 20% no Trabalho 2 | Domínio com Equipamento, subclasses e comportamento polimórfico; ORM como adaptador | Reconstrução por tipo e fatores de exposição executáveis |
| Arrays JSON, 20% | Quatro arrays com ativos, vulnerabilidades, incidências e dependências; número novo preservado | Exportação após commit e teste de recarga; usuários/salas completos exigem backup SQL |
| Container por pelo menos 24 h, 45% | Configuração e ferramentas operacionais existentes mantidas | **Pendente execução e evidência reais no servidor docente.** Não se deduz disponibilidade do Dockerfile |
| Modelo linear, 15% | M, v, A, b, x, estabilidade, condição e solve; perfil puro preservado | Cenário manual e verificações independentes; risco herdado pode ultrapassar 10 |
| CRUD anterior, Enum, busca e tratamento de entradas | Mantidos e ampliados com número e fluxo contextual | Não confundir código classificatório com ID inteiro; erros de integração não viram dados inventados |
| Mais de duas branches e merges | Requisito depende do repositório Git verdadeiro | Um ZIP não comprova histórico. Não foi fabricado histórico nem feito push nesta revisão |
| Apresentação e domínio do código | Continua sendo responsabilidade do estudante | Em cinco minutos, priorizar cadastro, JSON/recarga, risco e evidência do container |

Critérios não são uma nota atribuída ao projeto: o docente avalia a execução e a
explicação. A existência de classes, arquivos ou comandos não comprova sozinha o requisito.

## Crítica ao escopo do próprio Sauron

O Sauron é maior que o necessário para esta entrega. Treze menus, recomendador
imunológico e cálculo numérico aumentam o conteúdo a defender. O próximo ganho
relevante é concluir a implantação e a observação de 24 horas, não acrescentar outro
subsistema. O sistema imune produz sugestões, não diagnóstico de malware; risco
linear não é probabilidade de invasão, e uma animação não mede propagação no tempo.

Não foram acrescentados React, outro servidor Node, novas bibliotecas gráficas,
centralidade sem finalidade operacional, nmap, SSH remoto, armazenamento de
credenciais ou integrações generativas. Não eram necessários para as melhorias
selecionadas e aumentariam o custo de instalação e verificação.

## Fontes

- Arquivo enviado: `Inventario-Ativos-TI-main.zip`, especialmente os caminhos
  identificados na tabela de achados.
- `Avaliacao_Sprints_1_e_2_versao_2_0_2026_2(1).pdf`, Tabela 1 e condições.
- `Trabalho_2.pdf`, Seções 1, 2, 4 e Tabela 1.
- Django: https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- Django: https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/
- DRF: https://www.django-rest-framework.org/api-guide/permissions/

As limitações e os resultados da execução desta revisão estão em `VALIDACAO.md`.
