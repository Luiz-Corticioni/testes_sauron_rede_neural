# E-mail e verificação em duas etapas

Cadastro inicial local: `python manage.py cadastrar_administrador --usuario admin` cria somente o primeiro administrador, sem exigir login, dispositivo MFA ou e-mail. Pede senha e confirmação; e-mail é opcional. Esse cadastro não autentica a conta. A mesma exceção vale para a opção de primeiro administrador no terminal. Administradores adicionais seguem o fluxo autenticado.

Toda nova sessão web ou CLI exige segundo fator. Administradores, superusuários e qualquer conta com permissão de escrita ou decisão devem usar TOTP. E-mail é permitido somente para contas sem esses privilégios e deve ser apresentado novamente a cada sessão. Confirmação anterior do endereço não libera sessões futuras.

Primeiro acesso administrativo: após criar a conta, execute localmente `python manage.py provisionar_mfa --usuario NOME`. Cadastre a URI secreta exibida em um aplicativo autenticador; faça login e confirme senha mais TOTP. A criação de conta no terminal não autentica automaticamente.

Recuperação: o responsável pelo servidor deve verificar a identidade por procedimento externo e executar `python manage.py provisionar_mfa --usuario NOME --substituir --motivo "ticket e justificativa"`. O dispositivo antigo é removido, sessões com ele deixam de passar pelo MFA e um novo dispositivo não confirmado é emitido. Não use este comando sem acesso autorizado ao servidor. A URI não deve ser incluída em tickets, relatórios ou logs compartilhados.

Gestão de usuários e grupos no Django Admin é restrita a superusuários, mesmo quando uma conta staff recebe permissões `auth.*`. Usuários sem staff recebem 403 na área administrativa após MFA.

## Configurar o Gmail

1. Ative a verificação em duas etapas na conta Google que enviará as mensagens e crie uma [senha de aplicativo](https://support.google.com/accounts/answer/185833?hl=pt-BR). Ela não é a senha habitual da conta. Algumas contas de organizações ou com políticas específicas não permitem senhas de aplicativo; nesse caso, consulte o administrador da conta ou use outro servidor SMTP compatível.
2. No arquivo `.env` da pasta do Sauron, edite ou acrescente as linhas abaixo, substituindo os valores pelos da sua conta. Em instalações antigas, as linhas podem ainda não existir. Não compartilhe a senha nem publique o `.env`; restrinja o acesso ao arquivo.

```dotenv
SAURON_EMAIL_ENABLED=1
SAURON_EMAIL_HOST=smtp.gmail.com
SAURON_EMAIL_PORT=587
SAURON_EMAIL_USER=seu.endereco@gmail.com
SAURON_EMAIL_PASSWORD=sua_senha_de_aplicativo
SAURON_EMAIL_FROM=seu.endereco@gmail.com
SAURON_EMAIL_USE_TLS=1
SAURON_EMAIL_USE_SSL=0
```

O Gmail usa SMTP autenticado com TLS na porta 587; consulte as [configurações oficiais do Gmail](https://support.google.com/mail/answer/7104828?hl=pt-BR). Se alterar a senha da conta Google, pode ser necessário criar outra senha de aplicativo. Reinicie o Sauron após alterar o `.env`.

## Atualizar e testar

Antes de atualizar uma instalação existente, faça um backup cifrado e pare os processos do Sauron. No Fedora/RHEL, execute `bash instalar_linux.sh --atualizar`; no Windows, execute o instalador `.bat` do projeto para preparar o ambiente e aplicar as migrações. Os backups desta versão não contêm sessões nem códigos de e-mail pendentes; após restaurá-los, faça login novamente.

A verificação abaixo lê a configuração sem enviar mensagens. Execute os comandos na pasta do projeto:

```powershell
# Windows, PowerShell
.\.venv\Scripts\python.exe manage.py diagnosticar_email
```

```bash
# Linux
.venv-linux/bin/python manage.py diagnosticar_email
```

Para enviar uma mensagem de teste sem código, acrescente `--enviar-para seu.endereco@gmail.com` ao comando. Uma resposta de aceitação informa apenas que o servidor SMTP aceitou a mensagem; confira a caixa de entrada e o spam. Se falhar, revise as configurações e as políticas da conta Google.

## Entrar e recuperar o acesso

Cadastre um endereço válido ao criar um usuário. Com o envio configurado, um código é enviado depois que o cadastro é concluído. Na tela de entrada, informe usuário e senha; na etapa seguinte, digite a senha e o código recebido. Se necessário, use o botão para solicitar outro código. O código vale cinco minutos e só pode ser usado uma vez. Há intervalo mínimo entre envios e limites de tentativas e de reenvios.

Para um administrador já existente que não possui endereço correto, ajuste-o localmente com o comando abaixo, usando o executável Python do ambiente do Sauron. A mudança invalida a confirmação anterior e envia novo código quando o SMTP está configurado.

```text
python manage.py definir_email_usuario --usuario NOME_DO_USUARIO --email endereco@exemplo.com
```

Em Windows, substitua `python` por `.\.venv\Scripts\python.exe`; em Linux, por `.venv-linux/bin/python`. A senha da conta ainda será exigida na verificação. O autenticador TOTP continua disponível como alternativa; consulte a documentação de provisionamento de MFA do projeto.

A segurança da caixa de e-mail influencia essa alternativa. O segundo fator fortalece o controle de acesso, mas não garante sozinho confidencialidade, integridade e disponibilidade: permissões, auditoria, backups e operação também são necessários.
