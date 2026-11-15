# Ensaio Docker e varredura — 15/11/2026

[Relatório da etapa](RELATORIO_MELHORIAS_CURADORIA_2026-11-15.md) · [Roadmap](curadoria/06-roadmap-recomendacoes.md)

## Resultado operacional

Docker Desktop 4.99.0, engine Linux 29.9.3 e Compose 5.7.0. Imagem construída no Windows, branch melhorias-curadoria em 28af89b; dependências e índices de pacotes obtidos na construção. Projeto Compose isolado `sauroncuradoriateste`, com `.env` privado, HTTP somente em 127.0.0.1 e rotinas externas desabilitadas.

`preparar` terminou com código 0; web e agendador ficaram saudáveis; `/api/saude/` retornou HTTP 200. `seed_demo --operacional` concluiu; após reinício do web, foram contados quatro ativos e seis incidências de demonstração. Isso verifica inicialização e persistência simples, não autenticação, carga ou produção.

## Trivy: imagem construída

Trivy 0.76.2, imagem do scanner `sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb`, scanner de vulnerabilidades, HIGH e CRITICAL, base obtida em 15/11/2026. A imagem foi exportada com `docker save` e analisada pelo arquivo, sem montar o socket Docker. Debian 13.7; 47 ocorrências HIGH, zero CRITICAL, 11 CVEs distintos. Não há versão corrigida informada para estas ocorrências pela base usada, o que não comprova exploração nem elimina a necessidade de atualização e acompanhamento.

Cada linha abaixo é uma combinação de CVE e pacote, não uma vulnerabilidade independente. A coluna de estado reproduz a classificação do scanner; a aplicabilidade não foi verificada individualmente. O relatório bruto fica localmente em `work/varredura-sauron/trivy.json` e não contém credenciais nem o conteúdo do volume de dados.

| CVE | Pacote | Versão instalada | Estado informado | Versão corrigida |
|---|---|---|---|---|
| CVE-2025-69720 | libncursesw6 | 6.5+20250216-2 | affected | não informada |
| CVE-2025-69720 | libtinfo6 | 6.5+20250216-2 | affected | não informada |
| CVE-2025-69720 | ncurses-base | 6.5+20250216-2 | affected | não informada |
| CVE-2025-69720 | ncurses-bin | 6.5+20250216-2 | affected | não informada |
| CVE-2026-119373 | libsqlite3-0 | 3.46.1-7+deb13u2 | affected | não informada |
| CVE-2026-119374 | libsqlite3-0 | 3.46.1-7+deb13u2 | affected | não informada |
| CVE-2026-119379 | libsqlite3-0 | 3.46.1-7+deb13u2 | affected | não informada |
| CVE-2026-16742 | libsystemd0 | 257.13-1~deb13u1 | affected | não informada |
| CVE-2026-16742 | libudev1 | 257.13-1~deb13u1 | affected | não informada |
| CVE-2026-54369 | libacl1 | 2.3.2-2+b1 | affected | não informada |
| CVE-2026-76642 | bsdutils | 1:2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-76642 | libblkid1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-76642 | liblastlog2-2 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-76642 | libmount1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-76642 | libsmartcols1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-76642 | libuuid1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-76642 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-76642 | mount | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-76642 | util-linux | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78408 | bsdutils | 1:2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78408 | libblkid1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78408 | liblastlog2-2 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78408 | libmount1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78408 | libsmartcols1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78408 | libuuid1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78408 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78408 | mount | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78408 | util-linux | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78409 | bsdutils | 1:2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78409 | libblkid1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78409 | liblastlog2-2 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78409 | libmount1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78409 | libsmartcols1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78409 | libuuid1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78409 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78409 | mount | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78409 | util-linux | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78410 | bsdutils | 1:2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78410 | libblkid1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78410 | liblastlog2-2 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78410 | libmount1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78410 | libsmartcols1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78410 | libuuid1 | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78410 | login | 1:4.16.0-2+really2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78410 | mount | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-78410 | util-linux | 2.41.5-0+deb13u1 | affected | não informada |
| CVE-2026-9538 | perl-base | 5.40.1-6+deb13u1 | fix_deferred | não informada |

As correções disponíveis do Debian foram aplicadas durante a construção (o log registrou atualização de zlib). Não houve nova imagem ou comparação antes/depois específica para estes achados. Não foi desabilitado o bloqueio de HIGH/CRITICAL do CI. Necessário confirmar por CVE o estado no fornecedor, analisar exposição e repetir a varredura após correções; Q3 permanece aberto.

## Carga sintética preliminar

O script `scripts/testar_carga.py` foi executado em containers isolados, sem rede externa, 1 CPU, limite de processos 256 e sem swap adicional. A imagem empregou o mesmo código de hash Argon2 configurado na aplicação. Os testes com limites de 512 MiB e 1 GiB encerraram com código 137 e `OOMKilled=true`, sem resultados de latência ou 100 sessões. A repetição instrumentada de 512 MiB alcançou a etapa `login_senha_totp_gradual_mesmo_ip`, com até dez requisições simultâneas, antes de ser encerrada por memória.

O script inicia seu próprio servidor WSGI multithread e um banco temporário; **não** testa o Gunicorn de um worker e duas threads nem o caminho de rede dos serviços do Compose. Logo, o resultado não demonstra quantos usuários o Compose suporta nem que o serviço web isolado falhará da mesma forma. Não foram obtidos pico confiável de RAM, p50/p95, conclusão de MFA ou contagem de 429. Para concluir Q4, é necessário gerar carga no processo Gunicorn real, com contas e banco descartáveis, métricas coletadas e duas configurações; evitar reduzir o custo Argon2 para produzir um resultado favorável.

Correção pequena no script: o campo de relatório que dizia PBKDF2 era fixo e desatualizado; agora informa o algoritmo do hash efetivamente gerado, e as etapas de preparação e execução são identificadas no log. Nenhum fator de custo de senha foi alterado.

## Verificação adicional no Gunicorn do Compose

Em uma segunda instância `sauronmedicao`, volume próprio e porta local 2229, foram criadas 100 contas sintéticas (quatro administrativas) e dispositivos TOTP. O cliente HTTP realizou senha, TOTP e acesso à página autenticada, com até 10 clientes concorrentes e IP de origem compartilhado. Com limite de 512 MiB e 1 CPU, os 100 fluxos concluíram: duração 75,95 s; p50 de 7,59 s; p95 de 8,38 s; máximo de 9,13 s; nenhum 429 ou erro registrado pelo cliente. O pico do cgroup observado foi 320.765.952 bytes, incluindo a preparação da instância; não houve OOM ou reinício do serviço web. É um ensaio local, sem TLS, com dados sintéticos e carga gradual; não comprova 100 logins ao mesmo tempo, desempenho em produção nem teste de e-mail ou toda a matriz de permissões.

Consulta pontual ao rastreador do fornecedor em 15/11/2026: o Debian classifica [CVE-2026-76642 em trixie como vulnerável](https://security-tracker.debian.org/tracker/CVE-2026-76642) e informa que a correção de [CVE-2026-9538 em Perl está adiada](https://security-tracker.debian.org/tracker/CVE-2026-9538). Estas consultas não substituem a análise individual dos demais achados.

No mesmo serviço, com limite temporário ajustado para 1 GiB e mantendo 1 CPU e dois threads Gunicorn, uma segunda execução concluiu 100 de 100 fluxos em 67,75 s (p50 6,80 s; p95 8,06 s; máximo 8,50 s), sem erros ou 429. O pico cumulativo do cgroup após ambas as execuções foi 321.429.504 bytes; o contador não foi reiniciado entre execuções e inclui a preparação. Não houve OOM nem reinício. Houve atividade concorrente da suíte de testes no host durante essa segunda medição, de modo que as latências não são comparação controlada entre limites. O cliente e os dados sintéticos foram preparados para este ensaio, e os resultados não substituem um procedimento de carga reproduzível e validado em produção.

## Cem clientes iniciados simultaneamente

Em instância separada, Gunicorn com um worker e duas threads, 1 CPU, 512 MiB, mesmo IP de origem e limites normais de autenticação, 100 clientes no mesmo host fizeram GET da tela de login e foram liberados por barreira simultaneamente para enviar senha. No primeiro ensaio, 100 concluíram senha, TOTP e acesso ao guia em 78,67 s; p50/p95 do fluxo completo 78,00/78,53 s. Em outra execução, 4 administradores e 96 contas sem privilégios de equipe completaram login e verificação da administração em 76,50 s (p50/p95 75,79/76,39 s), com 200 para os administradores e 403 para os demais.

Após atribuir o grupo padrão Operadores às 96 contas, uma terceira execução concluiu 4 administradores e 96 operadores, com acesso administrativo 200/403 conforme esperado; duração 77,84 s, p50 77,21 s e p95 77,67 s. Não houve OOM ou reinício; pico cumulativo do cgroup após as execuções 325.095.424 bytes e saúde HTTP 200. Os tempos incluem a espera na barreira, todas as páginas e a verificação de administração; não representam exclusivamente tempo do login e revelam espera elevada sob essa rajada. Não houve 429 nos fluxos. A limitação de 20 usuários por IP considera reservas simultâneas e os dois threads do servidor restringem processamento paralelo; não extrapolar esse comportamento a outra configuração.

Resultados sintéticos locais e de curta duração, sem HTTPS, SMTP, multi-host ou medição de operação contínua; não demonstram capacidade de produção. A comparação 512 MiB/1 GiB anterior teve apenas 10 clientes concorrentes e não é uma comparação controlada entre configurações. [Roteiro para reprodução](TESTE_CARGA_DOCKER.md).

O roteiro versionado foi então reproduzido em novo projeto e banco vazios, já com a migração 0032: 100 fluxos iniciados por barreira, quatro administradores e 96 operadores concluíram senha, TOTP, guia e verificação de acesso administrativo; duração 75,77 s, p50 75,11 s e p95 75,56 s, incluindo barreira, páginas e verificação da administração. Pico cumulativo do serviço 322.576.384 bytes, sem OOM/reinício; saúde HTTP 200. Foi também executado um teste fictício de retenção no Docker: IP expirado eliminado e revisão recente preservada.
