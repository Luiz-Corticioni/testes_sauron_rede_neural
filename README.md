# Sauron, meu amor!

O Sauron é um inventário de ativos e vulnerabilidades que ajuda equipes técnicas e
responsáveis pelo negócio a entender dependências, acompanhar tratamentos e discutir
prioridades de segurança. Possui uma **interface gráfica no navegador** e uma
interface de terminal. É um protótipo de apoio à decisão: seus cálculos e sugestões
dependem dos dados cadastrados e não comprovam, por si só, uma invasão ou a segurança
do ambiente.

## Comece por aqui

| Quero... | Acesse |
|---|---|
| Instalar e abrir no meu computador Windows | [Primeiro acesso no Windows](docs/INSTALACAO_WINDOWS.md) |
| Instalar e abrir no Linux | [Instalação Linux](docs/INSTALACAO_LINUX.md) |
| Usar a interface, do cadastro aos relatórios | [Manual de uso](docs/GUIA_DE_USO.md) |
| Criar o primeiro administrador e configurar o segundo fator | [Primeiro administrador e login](#primeiro-administrador-e-login) e [e-mail e MFA](docs/EMAIL_E_MFA.md) |
| Entender os resultados sem conhecimento técnico profundo | [Guia simples das funcionalidades](docs/GUIA_SIMPLES_REANALISE_2026-11-10.md) |
| Executar com Docker ou implantar em servidor | [Docker](docs/DOCKER_TRABALHO_2.md) e [implantação](docs/IMPLANTACAO.md) |
| Acompanhar requisitos da Sprint 5 | [Rastreabilidade e pendências](docs/SPRINT5_RASTREABILIDADE.md) |
| Encontrar documentos técnicos e relatórios | [Índice da documentação](docs/README.md) |
| Conferir as alterações recentes de instalação e TOTP | [Relatório de 11/11/2026](docs/RELATORIO_INSTALACAO_E_TOTP_2026-11-11.md) |
| Entender o plano e as premissas da análise financeira | [Risco financeiro e contexto empresarial](docs/PLANO_RISCO_FINANCEIRO_2026-11-11.md) |
| Entender os componentes e critérios da interface | [Sistema visual](docs/DESIGN_SISTEMA.md) |
| Entender a correção de edições concorrentes | [Relatório de concorrência](docs/RELATORIO_CONCORRENCIA_2026-11-12.md) |

## Abrir a interface gráfica

Escolha **uma** forma de execução. Uma instalação local e uma instalação em Docker
podem ter bancos e usuários diferentes; criar uma conta em uma não a cria na outra.

### Windows, sem Docker

1. Tenha o projeto em uma pasta e instale Python 3.12. Abra um PowerShell nessa
   pasta, onde está o arquivo `manage.py`.
2. Siga a [instalação inicial no Windows](docs/INSTALACAO_WINDOWS.md), que prepara
   as dependências, o banco e o primeiro administrador. Faça essa preparação antes
   de tentar entrar pela primeira vez.
3. Inicie a interface:

   ```powershell
   & ".\.venv\Scripts\python.exe" scripts\iniciar_web.py
   ```

4. Mantenha o terminal aberto e acesse [http://127.0.0.1:8000/entrar/](http://127.0.0.1:8000/entrar/).
   Para encerrar, volte ao terminal e pressione `Ctrl+C`.

Após a preparação, `iniciar_sauron_web.bat` também inicia a interface. Para executar
as rotinas periódicas, mantenha o agendador em outro terminal, conforme o guia Windows.
Esse endereço HTTP é para o próprio computador, não para publicação na internet.

### Docker local

Com Docker Desktop e Compose funcionando, prepare o `.env` privado e execute
`docker compose up -d --build` na pasta do projeto. O roteiro completo, incluindo
comandos de cadastro e verificação, está em [Docker](docs/DOCKER_TRABALHO_2.md).
O Compose padrão publica o site localmente em
[http://127.0.0.1:2228/entrar/](http://127.0.0.1:2228/entrar/). A porta **8000**
continua sendo usada dentro do container; o navegador usa **2228** no computador.

Para Linux, consulte [instalação Linux](docs/INSTALACAO_LINUX.md). Para acesso
por outra máquina, domínio e HTTPS exigem configuração de servidor e rede: siga
[implantação](docs/IMPLANTACAO.md) e a seção de HTTPS do guia Docker.

## Primeiro administrador e login

O primeiro administrador do Sauron é criado **uma vez por banco novo**. Não há
usuário ou senha padrão obrigatórios. Na instalação Windows já preparada, execute:

```powershell
& ".\.venv\Scripts\python.exe" manage.py cadastrar_administrador --usuario admin --email seu_email@gmail.com
```

Troque o endereço pelo seu; o e-mail é opcional ao criar a conta. O comando solicita
uma senha escolhida por você e sua confirmação. `admin` é apenas um exemplo de
nome. O cadastro inicial não exige sessão administrativa, MFA ou SMTP previamente
configurados, mas **não inicia a sessão**. Se já existir um superusuário, o comando
recusa criar outro; use a conta existente e a administração autenticada.

No Docker, após `docker compose up -d --build`, o equivalente é:

```powershell
docker compose exec -it sauron python manage.py cadastrar_administrador --usuario admin --email seu_email@gmail.com
```

Depois configure pelo menos um segundo fator e entre na página de login:

1. Informe o usuário e a senha escolhidos.
2. Na página **Verificação em duas etapas**, use um dos métodos abaixo. Ela pede
   novamente a senha atual junto com o código.
3. Após entrar, abra **Guia rápido** no menu para consultar orientações dentro do site.

**Aplicativo autenticador (TOTP):** para a conta `admin` do exemplo, provisione o
dispositivo no terminal da instalação e cadastre a chave Base32 exibida em um aplicativo
autenticador compatível. A URI é um segredo; não a publique nem compartilhe.

```powershell
# Windows sem Docker
& ".\.venv\Scripts\python.exe" manage.py provisionar_mfa --usuario admin

# Docker: use este comando em vez do anterior
docker compose exec -it sauron python manage.py provisionar_mfa --usuario admin
```

Na tela de MFA, abra **Usar aplicativo autenticador**, informe a senha e o código
atual e clique em **Verificar autenticador**. Para cadastrar a chave no celular,
consulte o [passo a passo do TOTP](docs/EMAIL_E_MFA.md#aplicativo-autenticador-passo-a-passo).

**Código por e-mail:** configure primeiro uma conta de envio SMTP autorizada no
servidor, seguindo [e-mail e MFA](docs/EMAIL_E_MFA.md). Na tela, clique em **Enviar
código por e-mail** e informe senha e código recebido. O código vale cinco minutos
e pode ser usado uma vez. Um endereço Gmail ou UFU cadastrado como destinatário não
configura, sozinho, o serviço que envia as mensagens.

O administrador **do servidor ou do Windows** é uma conta externa ao Sauron. O
cadastro inicial não pede a senha dela, mas quem executa o comando precisa ter
acesso autorizado ao terminal e ao banco ou container da instalação. Para troca de
e-mail, recuperação de TOTP e diagnóstico de envio, consulte [e-mail e MFA](docs/EMAIL_E_MFA.md).

## Usar o inventário

Um percurso para conhecer o sistema com dados fictícios:

1. Em **Salas e subsetores** e **Ativos**, registre uma localização e um equipamento,
   indicando responsável e criticidade. A disponibilidade de telas depende das permissões.
2. Em **Vulnerabilidades**, registre ou consulte uma falha. Vincule-a ao ativo para
   criar uma **incidência**, isto é, o registro de que aquela falha afeta aquele ativo.
3. Em **Dependências**, registre se outro ativo depende do primeiro e confira a
   direção e o peso informados.
4. Consulte **Mapa de dependências**, **Matrizes** e **Prioridade de correção** para
   entender o modelo e comparar tratamentos. Simulações não aplicam correções reais.
5. Registre tratamento e evidências em **Incidências** e acompanhe **Alertas e decisões**.

Para instruções de CVE/KEV, EPSS, SSVC, software e documentos, relações por camada,
cobertura, perda financeira, Modo Euler, importação, exportação e administração,
use o [manual de uso](docs/GUIA_DE_USO.md). Para cada recurso ele indica onde começar,
o que informar, o que conferir e suas limitações.

## Documentação e situação do projeto

Os guias e relatórios ficam em [`docs/`](docs/README.md). O índice separa caminhos
para usuários, administradores, avaliadores e desenvolvedores. Relatórios de fases e
auditorias são históricos: datas, contagens de testes e funcionalidades futuras
descritas neles refletem a época de cada documento.

O Sauron não é um EDR nem detecta ou bloqueia malware por conta própria. Fontes
externas e e-mail dependem de rede e configuração. O backup do Sauron protege seus
dados, não os arquivos de toda a organização; mantenha cópias independentes e teste
a restauração. Veja [validação](docs/VALIDACAO.md), [reanálise e limites](docs/RELATORIO_REANALISE_2026-11-10.md)
e [requisitos do trabalho](docs/RELATORIO_TRABALHO_2.md). A execução no servidor por
24 horas e o envio real de MFA precisam ser comprovados no ambiente de destino.
