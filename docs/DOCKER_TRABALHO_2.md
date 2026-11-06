# Docker para o Trabalho 2

Situação: os arquivos existem; a construção, a reinicialização, a persistência e as
24 horas **precisam ser verificadas no servidor real**. Não são demonstradas por esta
documentação. Docker Engine/Compose e acesso ao servidor dependem do responsável
pelo ambiente; ter acesso à aplicação não concede acesso administrativo ao host.

Uma **imagem** é o pacote construído pelo Dockerfile; um **container** é uma instância
em execução da imagem; o **volume** conserva dados entre recriações de containers.
Neste projeto, o Compose cria um serviço de preparação, um web e um agendador. O
volume `sauron_dados` contém o SQLite, arquivos operacionais e exportações colocadas
em `/app/dados`. A interface web usa SQL como fonte principal; JSON é exportação
explícita. Um volume não substitui backup externo.

## Preparação e primeira execução

No servidor autorizado, na pasta do repositório, com Docker Compose e Python 3
disponíveis, execute uma linha de cada vez:

```sh
python3 scripts/preparar_ambiente.py
docker compose config
docker compose up -d --build
docker compose ps -a
docker compose logs --tail=100 preparar sauron agendador
docker compose exec -it sauron python manage.py cadastrar_administrador --usuario admin --email seu_endereco@gmail.com
docker compose exec -it sauron python manage.py provisionar_mfa --usuario admin
```

O gerador cria `.env` privado com chaves aleatórias e não sobrescreve o existente.
A senha do administrador é pedida no terminal. O último comando é uma opção para
configurar TOTP; para códigos por e-mail é necessário configurar SMTP, conforme
[EMAIL_E_MFA.md](EMAIL_E_MFA.md). Não cole senhas, QR codes, URI TOTP, `.env` ou
dados reais em logs, repositórios ou apresentações.

O exemplo gerado para `127.0.0.1` é HTTP local e não é adequado à internet. A porta
publicada pelo Compose fica em `127.0.0.1:8000` **do próprio servidor**. Para acesso
remoto, combine com o administrador o proxy HTTPS, domínio, certificado, firewall e
as variáveis de hosts/origens; use `SAURON_TRUST_PROXY=1` somente atrás de proxy
confiável que sobrescreva o cabeçalho encaminhado. Consulte [IMPLANTACAO.md](IMPLANTACAO.md).

### Servidor externo com proxy e HTTPS

O arquivo opcional `compose.https.yaml` acrescenta um proxy Caddy ao web e ao
agendador, semelhante à separação frontend/backend da referência. Sua imagem e
serviço são próprios; nenhum arquivo é gravado no outro repositório. O Caddy precisa
de um nome DNS real apontado para o servidor e das portas 80 e 443 acessíveis para
obter e renovar o certificado. Combine DNS, firewall, Docker e reinicializações com
o administrador do host. Se houver outro proxy institucional, integre-o apenas com
a equipe responsável; dois serviços não podem ocupar a mesma porta.
Consulte a [documentação oficial de HTTPS do Caddy](https://caddyserver.com/docs/quick-starts/https).

Para uma instalação **nova**, gere a configuração para o domínio escolhido:

```sh
python3 scripts/preparar_ambiente.py --host sauron.seu-dominio.org --https
```

O gerador não altera um `.env` existente. Edite o arquivo privado para conferir as
linhas abaixo, trocando o domínio; não gere nem compartilhe o arquivo com senhas:

```dotenv
SAURON_PUBLIC_HOST=sauron.seu-dominio.org
SAURON_ALLOWED_HOSTS=localhost,127.0.0.1,sauron.seu-dominio.org
SAURON_CSRF_TRUSTED_ORIGINS=https://sauron.seu-dominio.org
SAURON_SECURE_COOKIES=1
SAURON_SSL_REDIRECT=1
SAURON_HSTS_PRELOAD=0
```

Configure SMTP no mesmo `.env` seguindo [EMAIL_E_MFA.md](EMAIL_E_MFA.md), depois:

```sh
docker compose -f compose.yaml -f compose.https.yaml config --quiet
docker compose -f compose.yaml -f compose.https.yaml up -d --build
docker compose -f compose.yaml -f compose.https.yaml ps -a
docker compose -f compose.yaml -f compose.https.yaml logs --tail=50 proxy sauron
docker compose -f compose.yaml -f compose.https.yaml exec sauron python manage.py diagnosticar_email
docker compose -f compose.yaml -f compose.https.yaml exec sauron python manage.py diagnosticar_email --enviar-para seu.endereco@gmail.com
```

O último comando envia **uma mensagem real de teste** somente para o endereço que
você indicar; confirme na caixa de entrada e no spam. Depois teste o login completo
com um endereço Gmail e outro UFU que você controle. O servidor SMTP aceitar a
mensagem não comprova que ela chegou à caixa. Teste TOTP como alternativa.

O proxy tem IP `172.30.251.2` em uma rede interna separada; somente esse IP pode
informar ao Django que o acesso externo foi HTTPS. O proxy também participa de uma
rede própria com saída para emissão de certificados, enquanto o backend continua
publicado somente no loopback do host. Se a sub-rede conflitar com a rede local,
altere a sub-rede, o IP e o CIDR confiável juntos. Contêineres autorizados a ingressar
nessa rede ou operadores com acesso ao Docker ainda fazem parte da infraestrutura
confiável; restrinja o acesso ao daemon. Preserve os volumes `caddy_dados` e
`caddy_config`; perder os certificados pode provocar novas emissões.

Teste local no host depois que o serviço estiver saudável:

```sh
curl -fsS http://127.0.0.1:8000/api/saude/
docker compose exec sauron python manage.py exportar_json --saida /app/dados/exportacao
docker compose exec sauron python manage.py relatorio_sprint
docker compose exec sauron python manage.py relatorio_sql_sprint --limiar 0
```

A rota de saúde é apenas liveness; não comprova funcionamento de cada operação ou
entrega de mensagens. Os relatórios podem conter dados sensíveis: restrinja acesso.

## Verificar persistência e reinício

Use uma base de demonstração autorizada. Cadastre um ativo identificável, exporte os
JSONs, registre seu ID e verifique o volume com `docker volume ls`. Depois execute:

```sh
docker compose restart sauron agendador
docker compose ps -a
docker compose logs --tail=50 sauron agendador
```

Entre novamente e confira o mesmo ativo e arquivos. Para testar recriação do container,
`docker compose down` seguido de `docker compose up -d` preserva o volume nomeado;
confira o ativo de novo. **Não use `down -v`**: esse comando remove volumes. O teste
de reinício do servidor inteiro depende da autorização e da janela do administrador.
Após o reboot, repita `docker compose ps -a`, o `curl` local e a conferência do ativo.

## Evidência das 24 horas

Após o serviço atingir estado `healthy`, mantenha um processo de coleta no host por
24 horas efetivas (um terminal persistente ou serviço acompanhado pelo responsável):

```sh
python3 scripts/prova_24h.py --horas 24 --saida dados/prova-24h-nova.log
python3 scripts/verificar_disponibilidade.py dados/prova-24h-nova.log
```

O coletor identifica automaticamente o container do serviço `sauron`; também aceita
`--container ID`. O arquivo de saída deve ser novo, evitando misturar janelas de coleta.
O verificador exige 24 horas entre amostras, lacunas de até 90 segundos, estado
`running` e `healthy` e a mesma execução sem reinícios. Guarde evidência real de
build, logs, reboot, persistência e coleta; não edite datas para forçar aprovação.
O monitoramento amostral não garante disponibilidade entre amostras.
