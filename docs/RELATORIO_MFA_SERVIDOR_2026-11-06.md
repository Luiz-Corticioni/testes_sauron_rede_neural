# Proxy, MFA e revisão de segurança — 06/11/2026

## O que foi alterado

- `compose.https.yaml` acrescenta um proxy HTTPS separado do backend, com imagem
  Caddy versionada, volumes para certificados e rede interna. O backend mantém sua
  porta vinculada ao loopback do host. O proxy é o único serviço com o IP de origem
  que o Django aceita para `X-Forwarded-Proto` e para interpretação do IP do cliente.
  O guia descreve DNS, TLS, configuração de domínio, SMTP, primeiro acesso e testes.
- A inspiração foi a divisão proxy/backend do repositório informado. Sua criação de
  superusuário com senha fixa no entrypoint **não foi incorporada**: o Sauron já
  solicita a senha no comando de cadastro inicial e não autentica automaticamente.
- A validação SMTP agora recusa usuário sem senha ou senha sem usuário. Relays que
  não usam autenticação podem deixar os dois vazios. Conexão TLS ou SSL continua
  obrigatória; os logs não devem conter senha nem código de MFA.
- `scripts/testar_smtp_local.py` cria um servidor SMTP descartável no loopback,
  gera certificado efêmero, negocia STARTTLS, autenticação simulada e envia uma
  mensagem de teste para o próprio servidor. Não envia mensagem à internet. O CI
  foi ampliado para executar o teste, validar o Compose e iniciar o serviço base.
- O repositório e as dependências foram inspecionados para referências à OpenAI;
  esta alteração não adiciona integração, chave, chamada ou serviço da OpenAI. A
  chave opcional da NVD é de outro serviço e não é necessária ao uso básico.

## Verificações e limites

Nesta revisão, passaram 388 testes Django, seis testes pytest, o teste SMTP local,
`ruff`, a checagem Django de produção e a análise Bandit do código de aplicação.
As configurações YAML e a correspondência do IP do proxy foram verificadas
estaticamente. Avisos simulados de SMTP e fontes externas durante os testes não
representam teste contra serviços reais.
O Bandit mantém supressões preexistentes para subprocesso de restauração e acesso
HTTP a fontes externas; resultado limpo não equivale a ausência de riscos nesses pontos.
A consulta `pip-audit` não concluiu nesta revisão; reexecute-a no CI ou em um
ambiente com acesso ao serviço de vulnerabilidades antes da implantação.

A suíte de MFA verifica códigos de uso único, validade, limites, falha SMTP e
login de contas com endereços Gmail e UFU usando transporte em memória. O teste
SMTP local exercita o backend SMTP real do Django através de TLS e autenticação
simulada; **não verifica credenciais reais, entrega a destinatários ou políticas
externas**. São necessários uma conta SMTP autorizada, acesso de saída do servidor
e verificação de recebimento em caixas Gmail e UFU controladas pelo responsável.

O proxy HTTPS, a imagem e o Compose ainda precisam de `docker compose config`,
build e teste efetivo no servidor: o computador desta revisão não possui Docker.
O sucesso depende também de DNS, portas, certificado e configuração do provedor.
O resultado do CI após a publicação precisa ser conferido separadamente. O teste
de 24 horas e a verificação após reboot continuam pendentes.

Segurança não é certificada por uma revisão: mantenha dependências atualizadas,
proteja o `.env`, isole o acesso ao daemon Docker, teste a restauração de backups
e armazene âncoras de auditoria fora do volume operacional. O código anterior já
limita as tentativas e o reenvio de códigos, invalida códigos após uso e exige
nova verificação de MFA para cada sessão; testes automatizados não substituem
auditoria independente nem validação de infraestrutura real.
