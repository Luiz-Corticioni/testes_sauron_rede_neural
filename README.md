# Sauron — versão de apresentação sem MFA

**Esta branch desativa o segundo fator para todos os usuários, inclusive
administradores.** Ela existe como alternativa para uma apresentação com dados de
teste. Use apenas em ambiente local e controlado; não exponha esta versão à internet
ou use dados reais. A branch `main` mantém a política original de MFA.

O acesso continua exigindo **usuário e senha**, e as permissões de administrador,
limites de login, CSRF, auditoria e prazo de sessão continuam ativos. A interface de
terminal pode pedir novamente a senha em operações de escrita após o prazo de
reautenticação. Não há código de acesso por e-mail nem aplicativo autenticador.

## Baixar a branch

```sh
git clone --branch apresentacao-sem-mfa --single-branch https://github.com/Luiz-Corticioni/testes_sauron_rede_neural.git sauron-apresentacao
cd sauron-apresentacao
```

Use uma pasta e banco separados da instalação normal. Não execute migrações ou
operações de demonstração sobre o banco ou volume de produção.

## Iniciar no Windows, sem Docker

Com Python 3.12, abra PowerShell na pasta do projeto e execute:

```powershell
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" scripts\preparar_ambiente.py --desenvolvimento
& ".\.venv\Scripts\python.exe" manage.py preparar_servidor
& ".\.venv\Scripts\python.exe" manage.py cadastrar_administrador --usuario admin
& ".\.venv\Scripts\python.exe" scripts\iniciar_web.py
```

O comando solicita uma senha escolhida por você e sua confirmação; **não existe
senha padrão**. `admin` é apenas um exemplo. Se já existir superusuário no banco,
use a conta existente; o cadastro inicial recusa criar outro. Acesse
http://127.0.0.1:8000/entrar/, informe usuário e senha e entre diretamente.

## Iniciar com Docker

Com Docker Desktop iniciado, gere `.env` privado e construa o container:

```powershell
py -3.12 scripts\preparar_ambiente.py
docker compose -p sauron-apresentacao up -d --build
docker compose -p sauron-apresentacao ps -a
docker compose -p sauron-apresentacao exec -it sauron python manage.py cadastrar_administrador --usuario admin
```

O comando pede a senha sem mostrá-la no terminal. Abra
http://127.0.0.1:2228/entrar/ e entre com o usuário e a senha criados.
Para encerrar, use `docker compose -p sauron-apresentacao down`; não acrescente `-v` se quiser preservar
o volume. O Compose padrão cria serviços web e agendador. Não utilize o arquivo de
proxy público desta branch para disponibilizar a versão sem MFA na internet.

O nome do volume Docker depende do nome do projeto Compose. Se usar a mesma pasta
ou o mesmo nome de projeto da instalação normal, os dados podem ser compartilhados.
O nome `sauron-apresentacao` acima separa os volumes de outros projetos Compose.
Se a instalação normal já estiver usando a porta 2228, pare-a antes de iniciar esta.
Consulte o guia de apresentação abaixo.

## Usar os recursos

O [manual de uso](docs/GUIA_DE_USO.md) explica inventário, vulnerabilidades,
mapas, relatórios e cálculos. **Atenção:** os documentos históricos foram escritos
para a branch `main` e podem dizer que o MFA é obrigatório; nesta branch ele está
desativado. Consulte primeiro [instruções e relatório desta versão](docs/APRESENTACAO_SEM_MFA.md).

O Sauron apoia análise de inventário e não é uma ferramenta de detecção de malware.
