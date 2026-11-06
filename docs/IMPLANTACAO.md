> Atualização 01/11/2026, etapa 2: a migração 0021 cria o limite persistente de login. Execute `preparar_servidor` antes de iniciar os serviços e `verificar_implantacao --json` com a configuração real. Veja [as mudanças e limites](RELATORIO_ETAPA2_2026-11-01.md).

# Executar e publicar o Sauron

## Atualizar uma instalação existente

Extraia esta distribuição em uma pasta nova. Sobrepor arquivos não apaga os testes e
pastas antigos que estavam na instalação anterior. Antes de substituir uma instalação,
pare o servidor e o agendador e faça um backup pelo comando `python manage.py backup`.
Preserve o `.env` privado e a pasta de dados, incluindo o SQLite e os caches.

Copie os dados para a instalação nova, confira os caminhos em `SAURON_DATA_DIR` e
`SAURON_DB_PATH` e execute `python manage.py preparar_servidor` com as dependências instaladas.
As migrações mantidas fazem a atualização do banco. Não carregue `seed_demo` sobre dados reais.

A migração 0009 atribui `id_numerico` a cada ativo anterior, preservando códigos e vínculos.
Mantenha o backup: o número gerado é permanente nas próximas operações. Dados didáticos
antigos com fonte `Cenário demonstrativo` não são automaticamente convertidos em dados NVD;
revise essas vulnerabilidades antes de confirmar aplicabilidade em uma instalação real.

## Windows / PowerShell

Na pasta com `manage.py`, use Python 3.12:

Confirme `py -3.12 --version`. Se faltar o runtime, use `py install 3.12`, aguarde
e confirme novamente. Execute uma linha por vez; só avance se a anterior funcionar.

```powershell
py -3.12 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" scripts\preparar_ambiente.py
& ".\.venv\Scripts\python.exe" manage.py preparar_servidor
& ".\.venv\Scripts\python.exe" manage.py createsuperuser
& ".\.venv\Scripts\python.exe" scripts\iniciar_web.py
```

Abra http://127.0.0.1:8000/entrar/ e use o usuário criado. Não é necessário ativar
`Activate.ps1`. Também há `iniciar_sauron_web.bat`, que prepara o ambiente antes de abrir o servidor.

Terminal independente da interface gráfica:

```powershell
& ".\.venv\Scripts\python.exe" sauron.py
```

No menu 11, a opção 3 cria o primeiro administrador e a opção 6 prepara e inicia o site.
O servidor iniciado por `runserver` é para uso local. Para hospedagem, use WSGI e HTTPS.

## Linux / WSGI

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/preparar_ambiente.py --host sauron.example.org
```

Edite o `.env` privado para o domínio real:

```dotenv
SAURON_DEBUG=0
SAURON_ALLOWED_HOSTS=sauron.example.org,localhost,127.0.0.1
SAURON_CSRF_TRUSTED_ORIGINS=https://sauron.example.org
SAURON_SECURE_COOKIES=1
SAURON_SSL_REDIRECT=1
SAURON_TRUST_PROXY=1
SAURON_HSTS_PRELOAD=1
SAURON_SEED=0
```

`preparar_ambiente.py` gera a chave privada. Não envie `.env`, banco ou senhas ao GitHub.
Só use `SAURON_TRUST_PROXY=1` atrás de um proxy confiável que sobrescreva
`X-Forwarded-Proto`; esse cabeçalho não deve ser aceito diretamente de clientes externos.
HSTS preload é opcional: habilite apenas se essa política corresponder ao domínio.

```bash
.venv/bin/python manage.py preparar_servidor
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py check --deploy --fail-level WARNING
.venv/bin/python manage.py diagnosticar
.venv/bin/python -m gunicorn sauron_web.wsgi:application --bind 127.0.0.1:8000 --workers 2 --threads 2 --access-logfile - --error-logfile -
```

Configure o proxy para terminar TLS e encaminhar ao Gunicorn local. Exemplo de bloco Nginx
para um servidor com certificado já instalado:

```nginx
server {
    listen 80;
    server_name sauron.example.org;
    return 301 https://$host$request_uri;
}
server {
    listen 443 ssl;
    server_name sauron.example.org;
    ssl_certificate /etc/letsencrypt/live/sauron.example.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sauron.example.org/privkey.pem;
    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

O exemplo não instala nem emite certificados. Configure um supervisor de processo para
Gunicorn e o agendador e garanta escrita no diretório de dados. WhiteNoise serve os estáticos
preparados pelo collectstatic. Após mudar CSS/JS, execute `preparar_servidor` e reinicie os workers.
Para SQLite, mantenha o banco em disco local e faça backup; a concorrência de escrita é limitada.

## Docker

O passo a passo completo e as evidências ainda necessárias estão em
[Docker para o Trabalho 2](DOCKER_TRABALHO_2.md). Gere primeiro o `.env` privado.

```bash
docker compose up -d --build
docker compose exec sauron python manage.py createsuperuser
docker compose exec sauron python manage.py diagnosticar
docker compose exec sauron python manage.py sauron_cli
```

O Compose usa usuário não root, volume de dados, healthcheck e reinício automático.
O build prepara os estáticos; o entrypoint aplica migrações e verifica a instalação.
Em produção, coloque a porta atrás do proxy HTTPS. A rota pública de saúde é a única exceção
ao redirecionamento HTTPS no Django, permitindo o healthcheck interno do container.

Coleta operacional de disponibilidade:

```bash
python scripts/prova_24h.py --horas 24
python scripts/verificar_disponibilidade.py dados/prova_24h.log
```

Deixe a coleta terminar. O verificador rejeita duração insuficiente, reinícios, lacunas maiores
que 90 segundos e estados não saudáveis. Uma configuração de container não comprova 24 horas.

## CVEs na internet

No site: **CVE / KEV → código ou produto → Consultar NVD**. A opção de atualizar está marcada
por padrão. Desmarque-a se quiser reutilizar um cache NVD válido de até 24 horas.
**Revisar cadastro** preenche os dados, mas exige confirmação no formulário.

No terminal: **menu 7 → opção 5** para sugestões e consulta; **opção 3** para importar.
Sincronização por comando:

```powershell
& ".\.venv\Scripts\python.exe" manage.py sync_kev --nvd CVE-2021-44228 --forcar
& ".\.venv\Scripts\python.exe" manage.py sync_kev --forcar
```

O primeiro comando sincroniza CVEs na NVD; o segundo atualiza o catálogo CISA KEV.
Consultas por CPE são feitas pelas rotinas do menu 12 e geram vínculos sugeridos, não confirmados.
Uma chave NVD própria pode ser configurada em `NVD_API_KEY`. Sem chave, o cliente limita a
cinco consultas externas por janela de 30 segundos, compartilhadas entre processos.

## Diagnóstico de falhas

```powershell
& ".\.venv\Scripts\python.exe" manage.py diagnosticar
& ".\.venv\Scripts\python.exe" manage.py preparar_servidor
```

| Sintoma | Como investigar |
|---|---|
| Estáticos não preparados / manifesto ausente | Execute preparar_servidor; confira a escrita em STATIC_ROOT. |
| Banco ou migrações incompletos | Execute preparar_servidor; confira o caminho do SQLite e as permissões. |
| 403 no login ou POST | Confira domínio/origem CSRF, sessão e configurações de cookies HTTPS. |
| Fonte externa indisponível / 503 | Tente novamente depois; confira acesso HTTPS à NVD/CISA e limites da API. |
| 500 inesperado | Use o código X-Request-ID e consulte o traceback nos logs do servidor. |

Uma indisponibilidade externa não deve ser confundida com CVE inexistente. O sistema informa
404 quando a NVD retorna ausência de uma CVE completa e 503 em falhas de rede ou limite.

Referências oficiais: [Django: checklist de implantação](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/),
[Django: staticfiles](https://docs.djangoproject.com/en/5.2/ref/contrib/staticfiles/),
[NVD: API de vulnerabilidades](https://nvd.nist.gov/developers/vulnerabilities).

## Processos e heartbeat

`docker compose up --build` executa preparação/migração uma vez; web e agendador
são processos separados após conclusão dessa etapa. O entrypoint não exporta CMDB.
A rotina grava ultima_rotina.json ao concluir, inclusive status parcial e erros.
Healthchecks exigem heartbeat com idade <= 2x SAURON_ROTINAS_INTERVALO e o da web
também verifica HTTP. Ausência do arquivo falha após a tolerância de inicialização.
Um heartbeat recente comprova execução, não sucesso de todas as integrações; veja
status/erros no painel autenticado. O agendador limita cada subprocesso a 300 s.
SQLite admite um escritor por vez; trava transacional global serializa web/rotina.
Use um único container web e um agendador nesse modo, sem replicação horizontal.

## Saúde pública e detalhes

`/api/saude/` responde apenas `{"status":"ok"}`, antes de sessão/ORM, sem teste de
disco, tabelas ou versão. Limite padrão de 120 requisições por IP/minuto em memória,
por processo; use também limite no proxy se houver múltiplos workers.
`/api/saude/detalhe/` exige autenticação e view_registroauditoria e mantém a
introspecção operacional. O healthcheck Docker combina liveness mínima com heartbeat.
