# Fase 7 — Carga de usuários, cache e primeiro administrador

**Data:** 03/11/2026. **Base:** aplicação completa da fase 6, esquema 0026.

**Validação final: 370 testes aprovados, sem falhas, em 136,932 segundos.** São 21 testes novos sobre os 349 da fase 6, mais 12 cenários JavaScript e os ensaios HTTP descritos abaixo.

## Resposta sobre os 100 usuários

O Sauron sustentou **100 sessões distintas, quatro administradores e 96 leitores**, no ensaio HTTP local descrito abaixo. As quatro contas administrativas conseguiram escrever enquanto as outras 96 leram o painel. As 96 contas comuns receberam 403 ao tentar acessar a administração de usuários e também ao tentar escrever incidências. Auditoria, commit e rollback foram conferidos.

Isso comprova esse cenário de teste, não capacidade ilimitada ou homologação de produção. A entrada gradual completou senha e TOTP para todas as contas; uma rajada de logins de senha pelo mesmo IP encontrou a proteção de origem. Na execução final, 87 logins de senha foram aceitos e 13 receberam HTTP 429. Esses bloqueios são exibidos nos resultados, separados de erros inesperados. Os limites de autenticação não foram relaxados para aprovar o teste.

## Como foi medido

- Python 3.12.14, Django 5.2.17, Windows 11, 20 CPUs lógicas; SQLite/WAL, DEBUG=0 e cache de arquivos.
- Banco e configurações temporários, com 100 ativos, 10 vulnerabilidades, 100 incidências e 99 dependências. Nenhum banco, conta ou segredo real foi utilizado.
- Cem clientes HTTP com cookies próprios, senha verificada pelo PBKDF2 real e dispositivos TOTP distintos. Administradores têm `is_staff/is_superuser`; comuns têm permissões de leitura do inventário, sem escrita nem administração de usuários.
- Login gradual com concorrência 10; rodadas de leitura com concorrência cliente 100; carga mista com quatro escritores administrativos e 96 leitores; tentativas negativas e auditoria.
- Servidor WSGI de teste com threads e fila dimensionada para o ensaio, em loopback. Esse servidor não é recomendação para implantação. Não foi usado `runserver` para medir a carga.
- P95 das rodadas de 100 usa o 95º tempo ordenado. Tempos incluem cliente/servidor no mesmo computador, sem TLS, rede externa, renderização do navegador ou download de todos os estáticos. Não representam uma distribuição estatística de vários dias de produção.

### Resultados observados

| Rodada de 100 fluxos | SQL antes → depois | P95 antes → depois | UPDATEs de sessão antes → depois |
| --- | --- | --- | --- |
| Painel frio | 2892 → 811 | 3.133,05 ms → 609,88 ms | 100 → 0 |
| Painel aquecido | 2492 → 792 | 1.438,50 ms → 554,55 ms | 100 → 0 |
| API de risco | 1492 → 1292 | 1.163,95 ms → 429,16 ms | 100 → 0 |
| Lista de ativos | 1792 → 1598 | 1.902,27 ms → 1.080,95 ms | 100 → 3 |


As contagens SQL incluem autenticação, permissões, sessão e o conteúdo consultado. Não se eliminou a verificação de acesso para reduzir consultas. Cada etapa mede fluxos; login, escrita e tentativa negada podem conter mais de uma requisição HTTP.

| Fluxo final | Resultado | P95 observado |
| --- | --- | --- |
| Senha + TOTP, 100 contas em entrada gradual | 100/100 respostas conforme esperado | 6.219,41 ms |
| 4 administradores escrevendo e 96 leitores | 100/100 respostas conforme esperado | 615,50 ms |
| Administração: 4 acessos permitidos e 96 negados | 100/100 respostas conforme esperado | 2.277,98 ms |
| Escrita de incidências: 96 usuários comuns negados | 96/96 respostas conforme esperado | 1.550,62 ms |


A proporção de administradores não define sozinha a capacidade. Importam tamanho do inventário, custo das análises, número de pedidos por segundo, contenção de escrita, configuração do servidor e hardware. Noventa e seis leitores não equivalem a 96 operadores importando SBOMs ou executando cenários financeiros máximos ao mesmo tempo. O teste foi curto e não certifica resistência prolongada, múltiplos hosts ou um inventário com dezenas de milhares de ativos.

## O que mudou e por quê

### Cache de consultas e pré-carregamento

O resumo do painel passou a ser construído no serviço `aplicacao/painel.py` e reutilizado por **até 15 segundos**, com data/hora de geração visível. As chaves incluem instalação/banco, perfil, dia e permissões de leitura de alertas/certificados. Armazena dados, sem compartilhar HTML, cookies, identidade ou autorização. Os controles de rota, conta ativa, permissões e MFA continuam executando a cada requisição.

Gravações de ativos, vulnerabilidades, incidências, dependências, salas, alertas e certificados invalidam a geração após o commit. Alterações pendentes em uma transação não são publicadas como resumo compartilhado; rollback não contamina o cache. Escrita SQL direta ou atualizações fora dos serviços/sinais não equivalem a esse contrato de invalidação: o resumo tem, nesse caso, a validade máxima de 15s.

Risco e Monte Carlo mantêm as chaves por versão dos dados e parâmetros, com trava para que uma falta simultânea no cache não dispare a mesma reconstrução em todas as requisições. O painel e o risco usam famílias distintas de travas para permitir chamadas aninhadas. Há no máximo 64 arquivos por família, quatro famílias; isso limita o crescimento de travas. O mecanismo funciona entre threads e processos no mesmo host com os mesmos diretórios de dados/cache. Não é uma trava distribuída para múltiplos hosts.

`python manage.py aquecer_cache` prepara os dois perfis de risco quando há ativos e as variantes do painel, sem consultar fontes externas. `preparar_servidor` já o executa; `--sem-aquecer-cache` permite adiar. Para incluir o cenário financeiro padrão: `python manage.py aquecer_cache --incluir-financeiro`. O financeiro continua em 30 dias; falta de EPSS retorna indisponibilidade, não valores inventados. O resumo expira em 15s e reconstrói quando necessário; os cálculos versionados têm validade maior. Aquecimento não significa congelar dados durante a apresentação.

Cache é adequado a resultados reutilizáveis; não substitui consultas necessárias para verificar permissões ou refletir uma edição. Essa distinção acompanha o [framework de cache do Django](https://docs.djangoproject.com/en/5.2/topics/cache/).

### Concorrência do cache no Windows

A repetição do ensaio encontrou **um 503 em 100 acessos ao painel frio** na implementação intermediária. A investigação localizou leitura concorrente com regravação do arquivo: o fallback de cópia do backend original podia truncar/bloquear o destino durante a leitura. A evidência desse ensaio foi preservada, sem substituí-la pelo resultado final.

O backend `CacheArquivoAtomico` publica por substituição atômica, sem copiar por cima do arquivo consultado; repete por até cerca de um segundo erros transitórios de handle no Windows. Leitores recebem o conteúdo anterior inteiro ou o novo inteiro. Expiração continua sendo verificada mesmo se a remoção de um arquivo aberto precisar ser adiada. O cache usa namespace versão 2 para não reutilizar entradas anteriores à mudança.

Foram acrescentados testes de leitura/escrita concorrentes, substituição transitória e ausência de dados parciais, além da repetição real da carga. Falha persistente de permissão/disco continua sendo erro operacional; não é mascarada como sucesso. O backend mantém o formato do FileBasedCache e utiliza métodos internos do Django fixado em requirements: atualizações do framework devem repetir esses testes. O diretório de cache deve permanecer privado e fora do conteúdo servido por HTTP.

### Gravação de sessões e saúde da interface

Antes, cada GET autenticado atualizava a sessão no SQLite. O batimento de atividade passou a ser persistido em intervalos de até 30s. A autenticação e o dispositivo continuam verificados; o horário absoluto da sessão não foi ampliado. A sessão ociosa pode expirar até 30s mais cedo por esse agrupamento, nunca mais tarde por ele.

A verificação pública de saúde é reaproveitada no mesmo navegador/aba por até um minuto usando sessionStorage, reduzindo pedidos repetidos durante navegação e MFA. A interface informa que a resposta é recente. Um 429 agora aparece como verificação limitada, em vez de anunciar falsamente que o serviço está fora do ar. Falhas de rede/servidor continuam sendo indicadas. O limite de saúde do servidor foi preservado.

### Primeiro administrador sem MFA para cadastrar

Após preparar a instalação, execute:

```sh
python manage.py cadastrar_administrador --usuario admin
```

O comando local pede senha e confirmação. Não exige conta anterior, MFA, SMTP ou e-mail; `--email` é opcional. Não cria sessão nem um dispositivo automaticamente. A opção de primeiro administrador na CLI compartilha o mesmo serviço. Os validadores de senha permanecem ativos.

A criação é protegida por transação e trava de escrita; se já existe superusuário, inclusive inativo, o bootstrap recusa um segundo administrador. Não foi criada rota web pública ou opção global de desativar MFA. Para entrar depois do cadastro, a conta administrativa usa senha e TOTP, provisionado com `python manage.py provisionar_mfa --usuario admin`. Administradores adicionais continuam pelo fluxo autorizado. A exceção solicitada aplica-se à criação da primeira conta desta instalação, não a contas do sistema operacional ou de um domínio de rede.

Os guias Windows/Linux foram atualizados, inclusive corrigindo instruções antigas que sugeriam MFA por e-mail para administradores: a política atual exige TOTP para privilégios de escrita.

## Validações e evidências

- Suíte completa e testes novos: resultado na abertura e em `evidencias/fase7_carga_cache/TESTES.txt`.
- Doze cenários JavaScript: cache de saúde novo/válido/vencido/futuro, limitação, rede, armazenamento indisponível e tratamento HTTP/MFA/login.
- Ruff, Bandit, `pip check`, ausência de nova migração, configuração de produção e publicação dos estáticos.
- `pip-audit` on-line sem vulnerabilidades conhecidas nas oito versões declaradas em requirements, com `--no-deps --disable-pip`. Não é varredura completa de transitivas, sistema operacional ou imagem. Nenhuma dependência foi acrescentada.
- Duas tentativas reais e concorrentes de bootstrap em SQLite/WAL descartável: somente um primeiro administrador criado, a outra tentativa bloqueada e auditoria íntegra.
- Smoke test com DEBUG=0, bootstrap real em banco descartável, TOTP, CSRF, EPSS simulado, SSVC, SBOM/VEX, grafos, cobertura, financeiro, cache com zero consultas de conteúdo quando aquecido e commit/rollback.
- Carga HTTP real: resultados antes, intermediário com falha e final, com auditoria íntegra e instâncias temporárias encerradas.
- ZIP completo com CRC e manifesto SHA-256; sem bancos, contas, dispositivos, segredos ou ambiente virtual dos testes.

Para repetir a carga: `python scripts/testar_carga.py --saida resultado.json`. Para o JavaScript opcional: `node scripts/testar_javascript.cjs`. O programa de carga devolve erro se houver falhas inesperadas nos fluxos funcionais; a rajada de senha informa os bloqueios separadamente. Ele cria e remove sua própria base temporária. A comparação antes/depois foi realizada nesta máquina; o cenário misto e as verificações adicionais foram acrescentados na execução final, sem inventar valores de referência anteriores para essas etapas.

## Atualização e julgamento final

Preserve banco, `.env`, segredos e backup. Substitua o código pelo pacote, execute `python manage.py preparar_servidor` e reinicie web/agendador. Não há nova migração além de 0026 nem dependência de execução nova. O comando inicial não precisa ser executado novamente quando o administrador já existe.

O resultado atende ao cenário local testado de 100 sessões e ao balanço de leitura/escrita descrito. **Ainda não comprova 100 logins simultâneos sem bloqueio no mesmo IP**, nem dimensionamento de produção. O hash de senha continua custoso por finalidade de segurança; cache não deve acelerar autenticação reutilizando decisões antigas.

Para uma implantação real, dimensione o servidor de aplicação e teste banco/cache com o inventário e a concorrência previstos. SQLite pode atingir limites de contenção de escrita; [a documentação do Django descreve essa limitação](https://docs.djangoproject.com/en/5.2/ref/databases/#database-is-locked-errors). PostgreSQL e cache compartilhado entre hosts são próximos passos de homologação, não capacidades verificadas por este ensaio. O teste não inclui TLS/proxy, SMTP, fontes externas ao vivo, testes de navegador em cem máquinas ou teste prolongado. Não use o servidor de teste como produção; [a orientação de implantação do Django](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/) exige essa distinção.

Docker permanece adiado conforme combinado. Nenhum Dockerfile/Compose foi alterado ou imagem implantada nesta fase.
