# Relatório de revisão do Sauron — 01/11/2026

## Resultado e escopo

Esta revisão corrige a política de autenticação web/CLI, autorização administrativa, recuperação local de TOTP e configuração insegura de transporte para hosts externos. Preserva a aplicação completa do ZIP original, com código, dados demonstrativos, migrações, instaladores, testes e documentação. A cópia parcial anterior fica superada por esta entrega.

A análise é crítica: passar testes demonstra os cenários exercitados; não certifica segurança universal nem transforma um índice de risco em previsão de incidentes. As verificações de integração utilizam banco descartável, contas de teste e mocks de serviços externos. Não houve instalação em infraestrutura de produção, envio SMTP real ou teste de um provedor externo de identidade.

## Alterações e justificativas

| Área | Alteração | Motivo e comportamento esperado |
|---|---|---|
| MFA por sessão | `exige_mfa` exige segundo fator para toda conta autenticada | Confirmação antiga de e-mail e contas legadas sem dispositivo não liberam novos logins. |
| Privilégios | Staff, superusuário e qualquer permissão diferente de leitura exigem TOTP | Contas que escrevem ou decidem não podem usar e-mail para contornar o autenticador. |
| Web e serviço de e-mail | Recusa de autenticação privilegiada também em `verificar_codigo` | A regra vale além do formulário web e impede caminhos alternativos. |
| Terminal | Mesma política de métodos; dispositivo verificado é revalidado em cada operação | Promoção, remoção do dispositivo e mudança do endereço de e-mail invalidam o fator anterior. |
| Terminal | Conta e permissões são relidas; escrita exige reautenticação recente | Desativação e revogação de permissões passam a valer na sessão existente; a proteção de escrita acompanha a política web. |
| Criação de administrador | Criação na CLI não autentica automaticamente | Elimina acesso sem MFA após o cadastro. Conta existente precisa de autorização de superusuário para criar outra. |
| Recuperação de TOTP | `provisionar_mfa --substituir --motivo` revoga dispositivos anteriores e registra justificativa | Recuperação local auditável, com nova confirmação TOTP; sessões com o dispositivo removido deixam de passar pelo MFA. |
| Administração de identidades | Gestão de usuários e grupos limitada a superusuários | Staff com permissões `auth.*` não consegue promover a si próprio ou manipular grupos. |
| Acesso ao admin | Usuário sem staff recebe 403 e o link administrativo fica oculto | A barreira está no servidor; ocultação do link melhora a interface. |
| Operações de servidor na CLI | Inicialização/preparação web e exportação completa exigem superusuário | Um usuário comum não deve executar preparação do servidor ou exportar coleções para as quais não possui todas as permissões. |
| E-mail inicial | Contas privilegiadas não recebem código inicial de autenticação por e-mail | Evita oferecer um caminho que a política recusa; provisionamento TOTP fica explícito. |
| Produção | Hosts externos recusados sem cookies seguros, redirecionamento TLS e origens CSRF HTTPS | Impede configuração remota insegura por omissão. HTTP local continua disponível para instalação e desenvolvimento. |
| Compose | Porta publicada apenas em `127.0.0.1` | Evita publicação direta em todas as interfaces; acesso externo requer configuração consciente do proxy. |
| Interface e documentação | Tela MFA e guia distinguem contas de leitura e privilegiadas | Remove instruções incompatíveis com a política nova e descreve primeiro acesso/recuperação. |
| Testes | Cenários antigos de e-mail migrados para contas de leitura; testes novos verificam recusa privilegiada | Preserva teste do mecanismo de e-mail e verifica a política de acesso, sem remover cobertura para obter aprovação. |

## Resultado da validação final

- Suíte completa: **183 testes, 0 falhas**, em 60,356 segundos.
- Ruff: sem erros. Dependências: `pip check` aprovado. Migrações: nenhuma alteração pendente.
- Django `check --deploy --fail-level WARNING`: aprovado com configuração de produção sintética.
- Estáticos coletados com sucesso. Smoke em `DEBUG=0`: redirecionamento HTTPS, bloqueio antes de MFA, confirmação TOTP, painel e WhiteNoise aprovados em banco isolado; evidência em `evidencias/PRODUCAO_SMOKE.txt`. O teste não estabelece TLS em uma rede externa; simula requisições seguras pela pilha Django.
- Foram acrescentados 15 testes de segurança e integração aos 168 existentes.

## Verificações funcionais

Foram exercitados inventário, CVSS, comparação de versões, matching, risco esparso, Euler, Monte Carlo, histórico, decisões segregadas, auditoria, importação/exportação, backups/restauração, saúde e rotinas pelos testes existentes. A nova integração acessa 19 páginas locais com conta autorizada e quatro APIs (ativos, risco, histórico e auditoria), verifica status HTTP, JSON sem NaN/infinito e coerência da quantidade/IDs do inventário.

Testes de segurança novos verificam: nova sessão após confirmação de e-mail; conta legada sem dispositivo; leitor bloqueado no admin e em mutações; staff impedido de elevar privilégios mesmo com permissões auth; recusa de e-mail privilegiado na web/CLI; promoção de conta com fator e-mail; TOTP de outra conta; recuperação e confirmação do novo TOTP; ausência de autenticação automática no cadastro administrativo; revogação de permissões/conta na CLI; revogação de dispositivo na CLI; reautenticação para escrita; permissão de escrita sem staff; e recusa de configuração externa sem TLS.

O arquivo `evidencias/TESTES_ENTREGA.txt` registra a execução final. `evidencias/VERIFICACOES.txt` registra lint, migrações, check de produção, dependências e coleta de estáticos. Mensagens de indisponibilidade CVE e falha SMTP nos testes são respostas negativas deliberadamente simuladas, não comprovação de falha nos serviços reais.

## Primeiro acesso e atualização

1. Faça backup cifrado da instalação existente e pare seus processos antes da atualização. Preserve `.env`, banco e chaves; esta entrega não contém segredos de produção nem banco do usuário.
2. Instale as dependências e execute `python manage.py migrate` e `python manage.py collectstatic --noinput` no ambiente do projeto.
3. Crie o administrador pelo procedimento de instalação ou `python manage.py createsuperuser`.
4. Execute localmente `python manage.py provisionar_mfa --usuario NOME`, cadastre a URI secreta no autenticador e descarte a saída com segurança.
5. Entre com senha e confirme TOTP. Gerentes e operadores com escrita também precisam de dispositivo provisionado. Contas de leitura podem usar e-mail com SMTP configurado ou TOTP.
6. Em recuperação, confirme a identidade do titular fora da aplicação e execute `python manage.py provisionar_mfa --usuario NOME --substituir --motivo "ticket e justificativa"`.
7. Para host externo, configure TLS, cookies seguros, hosts, origens HTTPS e proxy confiável. O Compose publica apenas em localhost; adapte a rede do proxy de forma restrita. Execute `python manage.py check --deploy --fail-level WARNING` com a configuração real.

## Julgamento técnico e limites concretos

- O projeto tem controles e testes úteis, mas ainda possui concentração de funções e código de administração/CLI que exige manutenção cuidadosa. Nome de módulo e quantidade de funcionalidades não demonstram maturidade operacional.
- A política atual usa TOTP para privilégios. TOTP continua sujeito a phishing; WebAuthn/SSO não foi implementado nesta revisão. E-mail em contas de leitura tem proteção inferior e depende da segurança da caixa postal.
- A topologia suportada por esta entrega é um nó de aplicação com os processos compartilhando o mesmo diretório de dados e travas. Não foi implementado rate limiting distribuído entre hosts. Escalar réplicas independentes sem armazenamento/controle compartilhado invalida a suposição do limitador atual.
- Âncoras locais e backups no mesmo host não resistem ao comprometimento integral do host. O projeto já fornece `SAURON_AUDIT_SYSLOG`, `SAURON_AUDIT_ANCHOR_PATH` e `SAURON_BACKUP_DESTINO_ADICIONAL`; destino independente, retenção protegida, custódia de chaves e testes de desastre exigem infraestrutura real. Nenhum destino externo foi inventado ou configurado nesta revisão.
- Compatibilidade de dependências foi verificada com pip; isso não substitui uma auditoria atualizada de vulnerabilidades da cadeia de suprimentos. Container Linux, instaladores em distribuições reais e PostgreSQL não foram executados neste ambiente Windows.
- CVSS, propagação linear e similaridade continuam sendo medidas/modelos condicionados a hipóteses. Monte Carlo mantém uma extrapolação didática de EPSS constante e fallback estimado por CVSS. Valores finitos e reprodutíveis não demonstram calibração empírica ou validade financeira. Não existe histórico real rotulado no material que permita prometer essa validação.
- Os testes locais verificam respostas e regras de negócio. SMTP, NVD, CISA e EPSS reais precisam de homologação na rede de implantação. Não há garantia de ausência de falhas em todos os caminhos possíveis.

Esta entrega pode ser usada como base funcional revisada e testada para homologação. Liberação em produção exige validar os pontos de infraestrutura acima com os dados e a topologia reais.
