# Instalação no Windows

Este guia usa PowerShell e Python 3.12. Abra o terminal na pasta do projeto, onde está `manage.py`. O pacote não contém banco de dados, credenciais ou ambiente virtual: uma instalação nova começa sem dados de demonstração.

## Instalação inicial

Instale o Python 3.12 e confirme que o comando `py -3.12 --version` funciona. Execute:

```powershell
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" scripts\preparar_ambiente.py --desenvolvimento
& ".\.venv\Scripts\python.exe" manage.py preparar_servidor
& ".\.venv\Scripts\python.exe" manage.py cadastrar_administrador --usuario admin --email seu_email@gmail.com
```

O primeiro cadastro pede somente senha e confirmação, sem login, MFA ou SMTP prévios. E-mail é opcional com `--email`. O comando não inicia sessão e recusa criar outro administrador se já existir um. O `.env` contém chaves privadas; guarde-o com acesso restrito. `--desenvolvimento` é para uso local. Se o `.env` já existir, o preparador o preserva.

Inicie a interface web:

```powershell
& ".\.venv\Scripts\python.exe" scripts\iniciar_web.py
```

Abra http://127.0.0.1:8000/entrar/ e encerre com Ctrl+C. Como alternativa, após a preparação, execute `iniciar_sauron_web.bat`. Para a interface de terminal, execute `iniciar_sauron_terminal.bat` ou `& ".\.venv\Scripts\python.exe" sauron.py`.

Para entrar, configure o SMTP e use o código enviado ao e-mail cadastrado, ou execute `& ".\.venv\Scripts\python.exe" manage.py provisionar_mfa --usuario admin` para usar um autenticador TOTP. O cadastro inicial é independente do MFA. Consulte [e-mail e MFA](EMAIL_E_MFA.md).

Para as rotinas periódicas, mantenha um segundo PowerShell aberto na pasta do projeto:

```powershell
& ".\.venv\Scripts\python.exe" -u scripts\agendador.py
```

## Atualização de instalação existente

Pare a interface web, o terminal e o agendador. Preserve o código anterior, `.env`, banco e chaves; antes de aplicar uma atualização, crie um backup cifrado usando a versão que está em funcionamento:

```powershell
& ".\.venv\Scripts\python.exe" manage.py backup
```

Guarde a chave de backup separadamente e confirme seu procedimento de restauração. Atualize os arquivos do código sem substituir `.env`, banco, chaves ou backups, instale as dependências e aplique as migrações:

```powershell
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" manage.py preparar_servidor
```

A preparação altera o esquema do banco existente. Não execute esses comandos sobre dados que não deseja atualizar. Veja [implantação](IMPLANTACAO.md) para configuração em rede, HTTPS e operação; o servidor local de desenvolvimento não substitui uma implantação de produção.
