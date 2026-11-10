# Manual de uso do Sauron

> **Branch de apresentação:** o MFA está desativado. As instruções de MFA abaixo
> referem-se à branch `main`. Veja o [guia desta versão](APRESENTACAO_SEM_MFA.md).

[← Voltar ao início](../README.md) · [Índice de documentos](README.md) ·
[Login e MFA](EMAIL_E_MFA.md)

Este manual acompanha a interface web. Para instalá-la e entrar pela primeira vez,
comece no [README](../README.md). A interface abre no
navegador; não é um programa gráfico separado. A visibilidade de menus e as ações
possíveis dependem das permissões da conta. Uma tela pode aparecer no menu e ainda
retornar acesso negado se faltar alguma permissão exigida.

## 1. Primeiro acesso e perfis

1. O responsável prepara uma instalação e cria o primeiro administrador, escolhendo
   usuário e senha. Não há senha padrão. O cadastro não autentica a sessão.
2. Um responsável com acesso autorizado à instalação configura SMTP para e-mail ou
   provisiona um dispositivo TOTP. [Veja os comandos e a recuperação](EMAIL_E_MFA.md).
3. Na tela **Entrar**, informe usuário e senha. Na página seguinte, selecione o método
   de segundo fator, informe a senha novamente e o código. Para TOTP, abra **Usar
   aplicativo autenticador**; para e-mail, solicite o envio e verifique a caixa.
4. Após entrar, use **Guia rápido** no menu. Para sair, use o botão de saída no topo.

O administrador pode gerenciar contas no painel **Administração**. Contas comuns
devem receber apenas as permissões necessárias ao trabalho. A gestão de usuários e
grupos no Django Admin é restrita a superusuários; ser `staff` por si só não concede
essa gestão. Uma operação pode exigir MFA recente, mesmo após o login inicial.
Administração do servidor e administração do Sauron são responsabilidades distintas.

### Criar e orientar outras contas

1. Entre com um superusuário já autenticado e abra **Administração → Usuários**.
   Use a opção de adicionar usuário e defina os dados solicitados; o responsável
   deve entregar as credenciais por um canal seguro.
2. Na edição da conta, informe um e-mail válido se o método por e-mail será usado e
   atribua somente os grupos/permissões adequados. A preparação do servidor configura
   grupos chamados **Operadores**, **Gerentes** e **Auditores**; revise suas permissões
   no painel, pois cada ação exige permissões específicas. Configurar os grupos
   novamente redefine as permissões desses grupos para a política do projeto.
3. Para usar TOTP, um responsável com acesso autorizado ao terminal provisiona o
   dispositivo para o nome da nova conta, seguindo [e-mail e MFA](EMAIL_E_MFA.md).
   A URI TOTP é segredo e deve ser cadastrada apenas no autenticador do titular.
4. Peça ao usuário que entre com sua conta e conclua o segundo fator. Confira com
   uma conta de teste se ela acessa as telas permitidas e recebe bloqueio nas demais.

Uma conta sem permissão de leitura suficiente pode não abrir a página inicial mesmo
depois do login. Não marque `superusuário` apenas para contornar uma falta de acesso:
revise as permissões com o responsável.

## 2. Cadastre o ambiente

Use dados fictícios ao aprender. Um exemplo de sequência é cadastrar uma sala de
laboratório, um servidor de arquivos e um notebook que depende do servidor. Os
cadastros representam informações declaradas; o Sauron não confirma que a rede real
corresponde ao que foi informado.

### Salas e ativos

1. Em **Salas e subsetores**, use **Cadastrar** para registrar a localização quando
   necessário. Informe identificação e nome coerentes com sua organização.
2. Em **Ativos → Cadastrar ativo**, escolha tipo, nome, fabricante e demais campos
   solicitados, como responsável, localização e criticidade. Confira antes de salvar.
3. Na lista de **Ativos**, filtre e abra o detalhe para conferir o identificador e as
   informações cadastradas. Use as ações disponíveis na página para editar, vincular
   falhas ou cadastrar dependências, conforme sua permissão.

A criticidade e os campos de confidencialidade, integridade e disponibilidade são
informações declaradas. Documente os critérios de sua organização para compará-los.

### Software e documentos de componentes

Em **Software**, consulte ou cadastre componentes vinculados a ativos, informando
nome e versão quando conhecidos. O fluxo de documentos de inventário/SBOM e VEX pode
ser acessado a partir de **Software**. Para importar um documento, escolha o ativo e
o arquivo, valide primeiro e examine a prévia; só selecione a gravação após conferir
o resultado. O documento é uma declaração de componentes ou de aplicabilidade, não
uma prova automática de que uma vulnerabilidade existe ou deixou de existir.
Consulte [componentes, SBOM e VEX](RELATORIO_FASE3_COMPONENTES.md) para detalhes.

## 3. Registre e trate vulnerabilidades

1. Acesse **Vulnerabilidades** para consultar ou cadastrar uma falha. Informe
   descrição, categoria e CVSS quando disponível; uma CVE pública pode ser associada.
2. Para relacionar uma falha a um equipamento, abra o detalhe do ativo e use a ação
   de vinculação, ou utilize o cadastro de **Incidências** quando autorizado.
3. Em **Incidências**, confira ativo, vulnerabilidade, situação, prazo e evidência.
   Atualize o tratamento pelo fluxo disponível. Algumas decisões sensíveis exigem
   confirmação por outro usuário autorizado; uma solicitação não equivale à conclusão.
4. Acompanhe pendências em **Alertas e decisões**. Reconhecer um alerta registra a
   ciência; isso não corrige a causa. O MTTR exibido depende dos registros disponíveis.

### CVE, KEV, CVSS e EPSS

- Em **CVE / KEV**, procure uma CVE ou produto, consulte a NVD e revise os dados antes
  de confirmar um cadastro. A disponibilidade depende da rede e das fontes. Consulte
  o catálogo KEV para identificar uma evidência de exploração conhecida; não conclua
  automaticamente que o seu ativo foi comprometido.
- Em **Comparar CVSS**, examine as informações de CVSS 3.1 e 4.0 disponíveis. Vetor e
  versão importam: notas de versões distintas não são diretamente equivalentes.
  [Leia sobre a comparação](COMPARACAO_CVSS.md).
- Na lista ou detalhe de vulnerabilidades, confira EPSS e seu histórico quando houver
  observação. Na tela **Perda financeira**, um usuário autorizado pode solicitar
  **Consultar FIRST e atualizar EPSS**; a ação interativa consulta até 50 CVEs.
  Valor ausente ou desatualizado não significa risco zero.
- EPSS e KEV são sinais para priorização. Uma consulta da NVD, FIRST ou CISA pode
  falhar; confira os avisos e preserve o trabalho até conseguir atualizar a fonte.

### SSVC por ocorrência

Abra uma incidência e acesse **SSVC**. Informe os fatores solicitados, confira a
evidência e registre a avaliação conforme seu papel. A avaliação é específica da
ocorrência e das informações conhecidas naquele momento; revise-a quando o contexto
mudar. [Mais sobre SSVC](RELATORIO_FASE2_SSVC.md).

## 4. Entenda relações e impacto

### Dependências e matrizes

Em **Dependências**, registre o equipamento dependente, o fornecedor e o peso.
Exemplo: se uma aplicação precisa de um banco de dados, a aplicação é dependente e
o banco é fornecedor. O peso representa uma hipótese informada pelo operador.

Em **Mapa de dependências**, escolha o ativo para visualizar os vínculos e o alcance.
Em **Matrizes**, examine as incidências, os pesos e o risco próprio e efetivo. O
modelo puro soma as notas associadas e resolve a influência declarada na rede; o
perfil operacional acrescenta fatores internos. Pontos de risco não são CVSS nem
probabilidade de ataque. Confira dados de entrada e limitações antes de apresentar
o resultado. [Explicação matemática](EXPLICACAO_SAURON.md#6-modelo-de-risco).

### Relações por camada e qualidade

Em **Relações por camada → Cadastrar relação**, informe origem, destino, escopo,
fonte, evidência e datas de observação e revisão. Escolha a camada correta:

- **Rede:** tráfego declarado, protocolo e porta quando aplicáveis.
- **Identidade:** acesso declarado de um principal externo, sem registrar senha.
- **Negócio:** relação de fornecimento entre ativos no escopo indicado.

Use **Analisar alcance e cenários** para examinar caminhos estruturais; uma simulação
não modifica os cadastros. Em **Qualidade, cobertura e revisões**, usuários autorizados
podem declarar perímetros e registrar revisões, diferenciando relações revisadas,
ausência identificada e lacunas. Definir um perímetro influencia os grafos do escopo
correspondente. Uma cobertura declarada não comprova descoberta completa.
[Relações](RELATORIO_FASE4_RELACOES.md) · [Cobertura](RELATORIO_FASE5_COBERTURA.md).

## 5. Priorize e explore cenários

- **Visão geral:** ponto de partida para consultar o panorama e identificar dados
  pendentes; abra os detalhes antes de comunicar conclusões.
- **Prioridade de correção:** compare o ganho estimado ao corrigir falhas. O cenário
  simulado não altera uma incidência nem aplica atualizações aos equipamentos.
- **Perda financeira:** confira EPSS recente e com origem para as incidências
  elegíveis; informe custos e exposição adequados ao caso e compare correções
  hipotéticas. O horizonte é de **30 dias**. Custos padrão são exemplos, e o
  resultado não é uma previsão garantida nem um modelo FAIR completo.
- **Sistema imune:** consulte recomendações e tolerâncias. São hipóteses para triagem,
  não uma ferramenta de detecção de malware nem prova de vulnerabilidade. Pessoas
  autorizadas devem revisar evidências antes de tomar uma decisão.
- **Modo Euler:** escolha a operação matemática disponível, informe expressão e
  parâmetros exigidos e execute o cálculo. Comece com um exemplo simples da própria
  tela; métodos numéricos aproximam resultados e dependem dos parâmetros escolhidos.

Para explicações acessíveis e limites de cada recurso, consulte o
[guia simples](GUIA_SIMPLES_REANALISE_2026-11-10.md). O guia interno do site também
apresenta exemplos e definições para pessoas técnicas e responsáveis pelo negócio.

### Interface de terminal e API

Depois de preparar a instalação no Windows, abra `iniciar_sauron_terminal.bat` ou
execute `& ".\.venv\Scripts\python.exe" sauron.py` na pasta do projeto. No Docker,
use `docker compose exec -it sauron python manage.py sauron_cli`. Faça login com sua
conta e segundo fator e escolha as opções apresentadas pelo menu; permissões e
confirmações também se aplicam ali. Se o terminal e o site usarem instalações ou
bancos diferentes, seus cadastros e contas não serão compartilhados.

A API HTTP atende partes da interface e integrações autorizadas. As rotas de dados
utilizam os controles de sessão e permissão do Sauron; não presuma que um endereço
conhecido seja público ou que uma chamada de escrita dispense proteção CSRF. A rota
`/api/saude/` é uma verificação simples de disponibilidade e não testa todos os
serviços. Para a estrutura dos módulos e rotas, consulte [arquitetura](ARQUITETURA.md)
e o arquivo `inventario/web/urls.py` do projeto.

## 6. Importe, exporte e proteja dados

**Importar CSV:** acesse **Importar CSV**, escolha o arquivo e siga o fluxo de
validação/prévia indicado na tela. Corrija os erros e revise os dados antes de
confirmar a gravação. O modelo de importação acompanha o projeto.

**Exportar:** em **Exportar dados**, gere os relatórios disponíveis de acordo com sua
permissão. A exportação JSON administrativa é explícita e gera arrays com IDs e
vínculos; a interface principal usa banco SQL. Arquivos exportados podem conter
informações sensíveis: guarde-os em local autorizado.

**Auditoria:** em **Auditoria**, usuários autorizados consultam eventos e podem
verificar a cadeia. As âncoras e a chave precisam de proteção independente para
que a verificação tenha valor operacional.

**Backup:** o comando `python manage.py backup`, executado com o Python e ambiente
da instalação, cria backup lógico cifrado do Sauron. A restauração exige destino
SQLite novo e procedimento autorizado. Em Docker, use `docker compose exec sauron`
antes do comando. Guarde cópia e chave separadamente e teste restauração em ambiente
isolado. O volume Docker ou o backup do Sauron não substitui backup dos demais ativos.
[Detalhes de implantação](IMPLANTACAO.md).

## 7. Problemas comuns

| Sintoma | O que conferir |
|---|---|
| Site não abre | Mantenha o processo aberto; sem Docker use `127.0.0.1:8000`, com Compose padrão use `127.0.0.1:2228`. Confira mensagens do terminal ou `docker compose ps -a` e logs. |
| Não consigo criar o primeiro administrador | Execute após preparar o banco. Se já houver superusuário, use a conta existente. O comando precisa de acesso autorizado ao banco/container. |
| Senha aceita, mas não consigo concluir o login | Configure um TOTP para a conta ou SMTP e e-mail corretos; a criação da conta não inicia sessão nem dispensa o segundo fator. |
| Código de e-mail não chega | Confira SMTP, remetente, destinatário e spam. `diagnosticar_email --enviar-para` envia teste real ao endereço informado; consulte [o guia](EMAIL_E_MFA.md). |
| Página retorna 403 | A conta pode não possuir todas as permissões da ação ou ter verificação de sessão insuficiente. Solicite revisão ao administrador do Sauron. |
| Dados externos indisponíveis | Consulte avisos de rede, limites e fonte; ausência de resposta não significa ausência de vulnerabilidade. |
| Resultado parece incoerente | Revise incidências, estado dos ativos, datas, direção/peso das relações e premissas. Uma simulação depende da qualidade do cadastro. |

Não inclua senha, URI TOTP, chaves, `.env` ou dados sensíveis em mensagens de suporte.
