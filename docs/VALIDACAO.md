# Validação reproduzível

## Carga local de 100 usuários

Depois de instalar as dependências, execute `python scripts/testar_carga.py --saida carga-local.json`.
O script cria banco/dados/configuração temporários, 4 administradores e 96 leitores, faz login com
senha e TOTP reais e envia HTTP somente para loopback. Não utiliza o banco nem os segredos da
instalação. Os dados descartáveis são removidos ao terminar. Requer porta local livre e recursos
para 100 conexões concorrentes; não é um servidor de produção.

O JSON registra latência, contagens SQL, gravações de sessão, controle de acesso, carga mista,
coerência de cache e auditoria. A última etapa observa os bloqueios de uma rajada de login pelo
mesmo IP: respostas 429 são reportadas separadamente e não são escondidas pelo resultado geral.
Resultados e limites desta execução: [relatório da fase 7](RELATORIO_FASE7_CARGA_CACHE.md).

Testes JavaScript opcionais, sem bibliotecas externas: `node scripts/testar_javascript.cjs`.
Node é ferramenta de validação, não dependência do funcionamento do Sauron.

## Verificações de código

Use Python 3.12 e ambiente virtual. Instale:
```sh
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Configure .env privado por scripts/preparar_ambiente.py. Para validação local use
DEBUG=1 e SAURON_DATA_DIR apontando a diretório temporário, nunca ao banco real.

```sh
python manage.py check
python manage.py makemigrations --check
python manage.py migrate --noinput
python manage.py test
python -m pytest -q testes_pytest --cov=inventario.dominio --cov=inventario.matematica.risco --cov=inventario.infraestrutura.repositorio_json --cov-report=term-missing
ruff check .
bandit -r inventario sauron_web -x inventario/migrations
python scripts/check_producao.py
```

O último script gera segredos efêmeros e chama exatamente:
`python manage.py check --deploy --fail-level WARNING`, com DEBUG=0, hosts/origens
HTTPS, cookies seguros, redirect SSL e HSTS. Não escreve segredos no repositório.
A suíte principal usa unittest/Django, mocks e bloqueio de sockets. A suíte pytest
adicional cobre exemplos de persistência e risco; sua cobertura se refere somente
aos módulos indicados e não representa toda a aplicação.
Os resultados observados por fase estão no ledger REMEDIACAO.md; não se reproduzem
números históricos de testes que não foram executados nesta revisão.

CVSS 3.1: 2592 vetores base comparados a referência literal independente da FIRST
§7/Apêndice A, Roundup com inteiros e quatro scores públicos fixos.
Fonte: https://www.first.org/cvss/v3.1/specification-document
Euler: payloads de AST, domínios inválidos, overflow e limites levantam ValueError;
há verificação de ausência de chamadas eval/compile e testes de Euler/RK4.
Matching: fixture pequena rotulada mede precisão/recall; é sintética, sem garantia
de cobertura de produtos/configurações reais.
Risco: compara com solução densa (precisão ampliada no teste), confere resíduo e
mede 5000 ativos/4999 arestas/uma vulnerabilidade, sem serialização densa.
Backup: restaura banco novo, preserva auditoria e rejeita chave incorreta/sobrescrita.
Auditoria: SQL imutável, recomposição sem chave e truncamento após remover trigger.
MFA: token TOTP real, replay, sessão ociosa e reautenticação.
Liveness: teste proíbe SQL/escrita e verifica limite de requisições.

Ruff cobre E4/E7/E9/F; lambdas do estilo existente são permitidas. Reexportações e
imports tardios de inicialização são exceções pontuais no ruff.toml.
Bandit exclui migrações geradas e tem supressões locais: B310 após allowlist HTTPS/host;
B404/B603 para comandos fixos de Python/manage.py sem shell na restauração.
Os helpers _parte*.py são importados por migrações 0001/0006 e foram preservados.

Cadeia de suprimentos:
```sh
pip-compile --generate-hashes --output-file requirements.txt requirements.in
python -m pip install --require-hashes -r requirements.txt
pip-audit -r requirements.txt
cyclonedx-py requirements requirements.txt -o sbom.cdx.json
docker build -t sauron:ci .
trivy image --exit-code 1 --severity HIGH,CRITICAL sauron:ci
```
requirements.in contém dependências runtime; requirements-dev.txt contém ferramentas.
O lock com hashes deve ser gerado e validado no ambiente de entrega. A geração
remota local não concluiu nesta execução; requirements.txt não é apresentado como
lock com hashes. CI configura teste, Ruff, Bandit, pip-audit, SBOM e Trivy. Actions
aguardam pin por SHAs verificados (TODO explícito e Dependabot).
PostgreSQL, Docker/Trivy e serviço remoto de auditoria não foram validados localmente.

