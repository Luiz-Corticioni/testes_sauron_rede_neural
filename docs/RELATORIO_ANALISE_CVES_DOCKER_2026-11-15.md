# Análise de achados Docker — 15/11/2026

[Ensaio e pacotes](RELATORIO_DOCKER_CURADORIA_2026-11-15.md) · [Documentação](README.md)

## Escopo e CI

O [workflow 43683084065](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/actions/runs/43683084065) do commit `304679a` terminou com falha apenas no passo Trivy da imagem. As validações Ubuntu e Windows e os testes de instalação Windows, Ubuntu, Fedora e Rocky Linux passaram. Essa conclusão vale apenas para aquele commit e execução; não substitui a verificação de execuções posteriores.

O Trivy local 0.76.2 identificou 47 combinações CVE/pacote HIGH, 11 CVEs distintos e nenhum CRITICAL na imagem da etapa anterior `28af89b`; a lista por pacote/versão está no relatório vinculado. As consultas abaixo verificaram o rastreador Debian para a distribuição trixie em 15/11/2026. Todos constavam vulneráveis no trixie então; uma correção em sid/forky não significa que esteja disponível em trixie. O scan não foi repetido para a nova imagem de cenário financeiro; os resultados são temporais.

## Situação e aplicabilidade inicial

| CVE (fonte Debian) | Pacote-fonte | Condição / avaliação inicial |
|---|---|---|
| [CVE-2025-69720](https://security-tracker.debian.org/tracker/CVE-2025-69720) | ncurses | Sobrescrita no comando `infocmp`; binário existe na imagem. Busca textual nos diretórios do Sauron não encontrou chamada direta; isso não prova impossibilidade de execução indireta. |
| [CVE-2026-119373](https://security-tracker.debian.org/tracker/CVE-2026-119373) | sqlite3 | Exige operações específicas em FTS5 com dados e consultas preparados. A biblioteca carregada informa `ENABLE_FTS5`; não foi encontrada referência textual a FTS5 no código pesquisado. Não descartado para outros pontos de entrada ou bibliotecas. |
| [CVE-2026-119374](https://security-tracker.debian.org/tracker/CVE-2026-119374) | sqlite3 | Envolve índice FTS5 corrompido e secure-delete; `ENABLE_FTS5` está presente. Dependência de um arquivo de banco manipulado deve ser avaliada no procedimento de restauração. |
| [CVE-2026-119379](https://security-tracker.debian.org/tracker/CVE-2026-119379) | sqlite3 | Envolve aplicação de changesets pela extensão session; `ENABLE_SESSION` está presente. Não foi identificada chamada textual direta à função no código pesquisado. |
| [CVE-2026-16742](https://security-tracker.debian.org/tracker/CVE-2026-16742) | systemd | Afeta `systemd-homed`; `command -v systemd-homed` não o encontrou no PATH do container. Pacotes de bibliotecas continuam presentes; verificação não equivale a auditoria integral. |
| [CVE-2026-54369](https://security-tracker.debian.org/tracker/CVE-2026-54369) | acl | Envolve chamada privilegiada a funções de ACL em caminho controlável. Web opera como UID 10001, sem capabilities e com no-new-privileges; isso reduz condições, mas montagem/configuração diferente pode alterá-las. |
| [CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642) | util-linux | Envolve helpers privilegiados e opções de montagem; `mount` existe. O container da prévia não roda como root e remove capabilities; não estender conclusão ao host. |
| [CVE-2026-78408](https://security-tracker.debian.org/tracker/CVE-2026-78408) | util-linux | Requer uso privilegiado de `nsenter --join-cgroup`; `nsenter` existe, mas não foi encontrada chamada direta no código pesquisado. |
| [CVE-2026-78409](https://security-tracker.debian.org/tracker/CVE-2026-78409) | util-linux | Condições incluem opção de montagem e configuração autorizada em fstab; não foi provada uma rota pela aplicação. |
| [CVE-2026-78410](https://security-tracker.debian.org/tracker/CVE-2026-78410) | util-linux | Condições incluem montagem restrita autorizada via fstab e controle do caminho; não foi provada uma rota pela aplicação. |
| [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538) | perl | Exaustão de memória em Archive::Tar com arquivo malicioso; `perl` existe. Debian registra correção adiada para trixie; busca textual não achou uso direto do módulo no código pesquisado. |

## Ações e limitações

O Dockerfile já executa atualização dos pacotes disponíveis na construção e a política do CI permanece exigente para HIGH/CRITICAL. O rastreador indicava o trixie vulnerável para os onze casos: não se deve alegar que esses CVEs foram corrigidos nem importar pacotes de outra distribuição sem avaliação de compatibilidade. O UID sem privilégios, remoção de capabilities, raiz somente leitura e no-new-privileges são defesa em profundidade, não prova de segurança.

Monitorar atualizações do Debian, reconstruir com cache atualizado, repetir Trivy com base atualizada e executar testes e rollback. Confirmar alcance por fluxo e componentes efetivamente carregados, especialmente restauração de bancos SQLite, antes de classificar qualquer achado como não aplicável. O relatório é uma triagem, sem teste de exploração nem verificação formal; mudanças de imagem, host ou permissões invalidam conclusões anteriores.
