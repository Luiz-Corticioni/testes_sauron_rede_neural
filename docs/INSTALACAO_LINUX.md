# Instalar Sauron em Linux

## Baixar o projeto

Com Git instalado e conexão ao GitHub, abra o terminal na pasta em que deseja
criar a pasta `sauron` e execute:

```bash
git clone --branch main --single-branch https://github.com/Luiz-Corticioni/testes_sauron_rede_neural.git sauron
cd sauron
ls instalar_linux.sh requirements.txt manage.py
```

Os três nomes devem aparecer. Execute os comandos seguintes nessa pasta. O clone
baixa código e arquivos versionados; não traz o `.env`, o banco, senhas ou dados
privados de outra máquina. Caso o Git não esteja instalado no Fedora, alguém com
permissão de administração pode instalar o pacote `git` com `sudo dnf install git`.
Sem Git, abra a [branch principal no GitHub](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/tree/main),
selecione **Code → Download ZIP**, extraia o arquivo e abra um terminal dentro da
pasta extraída. Se o clone ou download não terminar, confira a mensagem de erro,
conexão, acesso ao GitHub e espaço livre; repetir os comandos de instalação não
recupera um download incompleto.

## Preparar e iniciar

Execute os comandos dentro da pasta descompactada do projeto, em uma sessão de
usuário comum. Não copie o ambiente `.venv` do Windows:
o instalador Linux usa `.venv-linux` e mantém o Python do sistema.

```bash
bash instalar_linux.sh --simular
bash instalar_linux.sh
bash iniciar_linux.sh --web
```

Se Python 3.12 com `venv`, SSL e SQLite já estiver disponível, o instalador o usa
sem solicitar `sudo`. Se não estiver, pode instalar pacotes do sistema via `dnf`
no Fedora/RHEL ou `apt-get` no Ubuntu 24.04, com acesso a `sudo`. Ele cria o ambiente virtual Python
3.12, instala as versões de `requirements.txt` usando wheels, verifica conflitos,
gera chaves privadas em `.env` se ele não existir, aplica migrações, configura os
grupos, publica arquivos estáticos, cria a primeira âncora e executa diagnósticos.
Apenas `dnf` usa sudo. Não instala ferramentas de auditoria/desenvolvimento como
parte do funcionamento normal. Rede é necessária para repositórios dnf e PyPI.
Sem wheel compatível com a arquitetura, a instalação interrompe com erro em vez de
compilar dependências implicitamente. Não cria senha padrão nem importa dados de exemplo.

Suporte automático de pacotes: Ubuntu 24.04; Fedora com pacote `python3.12`; RHEL e compatíveis (Rocky/Alma/
CentOS Stream) 9.4 ou posterior com os pacotes Python 3.12 do fornecedor. Em RHEL,
a assinatura e os repositórios oficiais precisam estar habilitados pelo administrador.
O script não habilita repositórios de terceiros. A disponibilidade pode variar por
versão/arquitetura; leia o erro do dnf. Não se comprovou execução real nessas
distribuições neste host Windows; a CI inclui containers Fedora/Rocky para esse teste.
Em outra distribuição ou versão, instale Python 3.12, `venv`, SSL e SQLite por um
meio adequado ao sistema e execute `bash instalar_linux.sh --sem-pacotes`.
O suporte depende também de wheels das dependências para sua arquitetura; não é
possível prometer compatibilidade com todas as distribuições e máquinas.

Sem sudo, peça ao administrador os pacotes listados em `--simular` e use:

```bash
bash instalar_linux.sh --sem-pacotes --python /usr/bin/python3.12
```

## Primeiro acesso

```bash
.venv-linux/bin/python manage.py cadastrar_administrador --usuario admin --email seu_email@ufu.br
```

O cadastro inicial exige somente senha e confirmação, sem login, MFA ou SMTP prévios.
E-mail é opcional com `--email`. O comando não inicia sessão nem cria administradores
adicionais quando já existe um. Para entrar na aplicação, execute
`.venv-linux/bin/python manage.py provisionar_mfa --usuario admin` e registre a URI
secreta em um aplicativo autenticador. Como alternativa, configure SMTP e use o
código enviado ao e-mail cadastrado, inclusive para contas administrativas. Consulte
[EMAIL_E_MFA.md](EMAIL_E_MFA.md).
Abra http://127.0.0.1:8000/entrar/ depois de iniciar `--web`.
Esse modo usa o servidor de desenvolvimento do Django e acesso local.

Para preencher **um banco de teste vazio** com o cenário fictício incluído no código:

```bash
.venv-linux/bin/python manage.py seed_demo
```

Esse comando não baixa os arquivos pessoais de outra instalação. Ele ignora um banco
que já contenha inventário. Dados anteriores exigem restauração ou importação autorizada.

Outras interfaces:

```bash
bash iniciar_linux.sh --terminal
# Em outro terminal, para rotinas e alertas periódicos:
bash iniciar_linux.sh --agendador
```

O agendador precisa permanecer em execução para executar rotinas periódicas;
a navegação web não o inicia. Para ensaios sem rede, configure
`SAURON_ROTINAS_SEM_REDE=1` no ambiente ou `.env`.

## Atualizar e diagnosticar

```bash
bash instalar_linux.sh --verificar
# Pare primeiro web, terminal e agendador; preserve também a versão antiga do código.
bash instalar_linux.sh --atualizar
```

A reexecução comum preserva `.env`, chaves e banco. Se houver migrações pendentes,
exige `--atualizar`. Uma atualização explícita verifica a auditoria e cria backup
lógico cifrado antes de migrar. Se o backup, a chave ou a auditoria falhar, não migra.
Mantenha as chaves de backup e HMAC em cópia privada separada: sem elas a recuperação
ou a verificação é inviável. Confirme recuperação em banco novo com o comando
`restaurar_backup --help`. A publicação do banco restaurado é exclusiva e ocorre
somente após verificação da cadeia; a recuperação isolada não atesta âncoras externas.
O backup pré-migração usa o esquema atual; se a versão nova não conseguir ler o
esquema antigo, o procedimento aborta e exige backup usando a versão anterior.

O diagnóstico verifica gravação, banco/migrações, templates, estáticos e auditoria,
sem imprimir chaves. Ele cria apenas arquivo temporário de escrita e o remove.
Para mais detalhes: `.venv-linux/bin/python manage.py diagnosticar --json`.

## Servidor com HTTPS

Para instalação nova, configure um nome DNS:

```bash
bash instalar_linux.sh --host sauron.exemplo.org --https
bash iniciar_linux.sh --servidor
```

Esse comando inicia Gunicorn em **127.0.0.1:8000**. Configure um proxy reverso
com certificado TLS válido para encaminhar as requisições a esse endereço,
sobrescrever `X-Forwarded-Proto` e `X-Forwarded-For`, e preservar o Host permitido.
No `.env`, configure `SAURON_TRUST_PROXY=1` e
`SAURON_TRUSTED_PROXIES=127.0.0.1/32,::1/128` se o proxy for local.
O protocolo encaminhado só será aceito quando vier desses endereços.
Sem proxy HTTPS configurado, esse modo não estará acessível corretamente pelo navegador.
O instalador não abre firewall, não altera SELinux e não emite certificados.

O `.env` existente é sempre preservado, inclusive se você passar outro host.
Para migrar uma instalação local para HTTPS, ajuste explicitamente os hosts,
origens CSRF, cookies seguros, redirecionamento HTTPS e proxy conforme `.env.example`.
Valide com `.venv-linux/bin/python manage.py check --deploy`.
Use uma conta de serviço sem privilégios e configure web/agendador como serviços
no supervisor da sua infraestrutura; os launchers ficam em primeiro plano.
As chaves e o banco devem ter acesso restrito. O script usa `umask 077` e cria
`.env` com modo 0600; ele não corrige permissões herdadas de cópias externas.

## Testes do instalador

```bash
bash -n instalar_linux.sh
bash scripts/test_instalador_linux.sh
SAURON_DEBUG=1 .venv-linux/bin/python manage.py test
```

O teste shell simula Python e Linux sem instalar pacotes, cobre caminhos com
espaços, preservação da configuração, falha do pip, versão de distribuição e modo
simulação. Os testes Python verificam ordem de backup/migração, reexecução e criação
privada das chaves. O job `instalacao-linux` da CI instala as dependências e prepara
uma instalação nova em containers Fedora e Rocky; estar configurado não significa
que esse job já tenha sido executado com sucesso.

Referências oficiais: [Python venv](https://docs.python.org/3/library/venv.html),
[Python paralelo no Fedora](https://developer.fedoraproject.org/tech/languages/python/multiple-pythons.html),
[Python no RHEL 9](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/9/html/installing_and_using_dynamic_programming_languages/assembly_installing-and-using-python_installing-and-using-dynamic-programming-languages),
[checklist de implantação Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/).
