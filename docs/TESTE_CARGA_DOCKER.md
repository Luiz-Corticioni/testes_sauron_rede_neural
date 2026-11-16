# Ensaio local de 100 clientes no Compose

[Documentação](README.md) · [Resultados observados](RELATORIO_DOCKER_CURADORIA_2026-11-15.md)

O procedimento cria 100 contas **sintéticas** num banco descartável próprio: quatro superusuários e 96 integrantes de Operadores. O cliente aguarda 100 requisições GET da página de login e depois libera simultaneamente as requisições de senha. Cada fluxo conclui TOTP e verifica acesso à administração (200 para os quatro administradores; 403 para os operadores). O alvo do cliente é fixo em `127.0.0.1:2230`. As contagens e tempos não contêm senhas; p50/p95 incluem espera na barreira e duração do fluxo completo, não apenas o tempo individual do hash.

Use somente numa máquina e projeto descartáveis. A fixture se recusa a operar sem `SAURON_CARGA_DESCARTAVEL=1` ou em banco que já tenha usuários ou ativos; isso é defesa adicional, não substitui a verificação do projeto Compose. O teste executa hashes Argon2 reais e pode consumir recursos. A senha e chaves TOTP são fictícias e ficam temporariamente em `credentials.json`; proteja e remova esse arquivo. O resultado não testa SMTP, comportamento multi-host, dados reais, acesso por outros endereços IP nem operação continuada.

## Exemplo no PowerShell, a partir da raiz do repositório

Pré-requisitos: Docker Desktop Linux ativo, Python e dependências do projeto instalados no ambiente atual, `.env` privado de teste com `SAURON_SEED=0`, porta 2230 disponível. Verifique se não existe um projeto Compose chamado `sauroncarga` antes de iniciar; nomes de projeto iguais compartilham recursos. O exemplo usa um diretório novo no TEMP, sem copiar dados reais.

```powershell
$repositorio = (Get-Location).Path
$env:SAURON_CARGA_DIR = Join-Path $env:TEMP ('sauron-carga-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $env:SAURON_CARGA_DIR | Out-Null
Copy-Item -LiteralPath scripts/carga_compose/preparar.py -Destination $env:SAURON_CARGA_DIR

docker compose -p sauroncarga -f compose.yaml -f scripts/carga_compose/compose.carga.yaml up -d --build
# Prossiga somente se a inicialização terminar sem erro.
docker compose -p sauroncarga -f compose.yaml -f scripts/carga_compose/compose.carga.yaml exec -T -e SAURON_CARGA_DESCARTAVEL=1 sauron python manage.py shell -c "exec(open('/bench/preparar.py', encoding='utf-8-sig').read())"
# Prossiga somente se a fixture confirmar o banco descartável.
Push-Location $env:SAURON_CARGA_DIR
python (Join-Path $repositorio 'scripts/carga_compose/cliente_100.py')
# Em outro projeto e banco descartável, compare também grupos de 10 ou 20:
# python (Join-Path $repositorio 'scripts/carga_compose/cliente_100.py') --concorrencia 10
# Opcional: bloqueia uma conta sintética por até 15 minutos.
python (Join-Path $repositorio 'scripts/carga_compose/tentativas_invalidas.py')
Pop-Location

docker inspect --format 'status={{.State.Status}} oom={{.State.OOMKilled}} reinicios={{.RestartCount}}' sauroncarga-sauron-1
docker exec sauroncarga-sauron-1 cat /sys/fs/cgroup/memory.peak
# Confira o HTTP 200 e o JSON de saúde após o teste.
Invoke-WebRequest http://127.0.0.1:2230/api/saude/
Remove-Item -LiteralPath (Join-Path $env:SAURON_CARGA_DIR 'credentials.json')
docker compose -p sauroncarga -f compose.yaml -f scripts/carga_compose/compose.carga.yaml down
```

O volume sintético continua existindo após `down`; não remova volumes de outros projetos. `memory.peak` é cumulativo desde a criação do container e inclui preparação. O cliente sai com código diferente de zero se os resultados de quatro administradores e 96 operadores não forem os esperados. O ensaio opcional de senha inválida espera cinco respostas de falha e uma resposta 429; ele bloqueia a conta sintética e deve rodar depois dos logins válidos. A versão da imagem, a carga concorrente da máquina, os limites do Docker e a política de autenticação devem ser registrados com os resultados.
