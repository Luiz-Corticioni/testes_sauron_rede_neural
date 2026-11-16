# Imagem Alpine: comparação e validação — 15/11/2026

## Por que mudar

A imagem anterior, baseada no Debian trixie, apresentou 47 combinações CVE/pacote HIGH em [varredura anterior](RELATORIO_CI_IMAGEM_2026-11-15.md). Naquele exame o scanner não informou versão corrigida para essas ocorrências. A alternativa foi avaliada em uma imagem separada antes de alterar o Dockerfile, sem desativar o Trivy nem importar pacotes Debian de outra versão.

A nova base é a imagem oficial Python 3.12 Alpine, fixada pelo digest de seu manifesto multi-arquitetura. Os pacotes disponíveis são atualizados durante a construção; o processo continua sob UID 10001, com os mesmos volumes e restrições do Compose. Um digest fixo não atualiza automaticamente a imagem base: é necessário revisar e atualizar o digest periodicamente. O índice do repositório também pode mudar entre construções, portanto a fixação da base não garante construção bit a bit idêntica.

## Evidências

- Imagem experimental construída para `linux/amd64` com Alpine 3.24.4; as dependências NumPy e SciPy foram instaladas em distribuições binárias musllinux.
- Trivy 0.76.2, com banco atualizado em 16/11 UTC, reconheceu 38 pacotes do sistema e os pacotes Python e não apontou ocorrências HIGH ou CRITICAL. Antes, a imagem Debian analisada apresentava 47 HIGH. A mudança de base removeu aqueles pacotes Debian da imagem; não significa que os CVEs tenham sido corrigidos no Debian nem que não existam outras falhas. O resultado depende da cobertura e da base do scanner.
- Com a rede desativada, passaram **479 testes Django** no container experimental. A primeira tentativa teve uma falha porque o teste de CI não encontrava `.github`, excluído da imagem de produção; após montar esse diretório e os testes somente para leitura, a suíte inteira passou.
- No Compose isolado, preparação terminou com código 0, web e agendador ficaram saudáveis e `/api/saude/` retornou 200. Os quatro ativos e seis incidências fictícias continuaram no volume após reinício do serviço. O fuso `America/Sao_Paulo` também foi carregado.
- O Dockerfile final foi construído com o digest fixado; uma segunda varredura do artefato final também não apontou HIGH ou CRITICAL. O workflow passou a executar a suíte dentro da imagem com rede desabilitada, além dos testes existentes e da varredura HIGH/CRITICAL. A confirmação do GitHub depende da execução do commit que contém a alteração.

## Limites e acompanhamento

Os ensaios foram feitos em `linux/amd64`; a existência de manifesto para outras arquiteturas não comprova que todas as dependências e funcionalidades funcionem nelas. A mudança para musl em vez de glibc altera o ambiente de execução: mantenha testes regressivos, especialmente para bibliotecas nativas, e valide a implantação real e backups antes de migrar dados. Não foram realizados teste de carga, operação por 24 horas ou auditoria de todas as bibliotecas nativas incorporadas aos wheels nesta etapa. Não se conclui que a imagem seja isenta de vulnerabilidades.

Se houver incompatibilidade, preserve o backup e retorne ao Dockerfile do commit anterior `cc4e3fe`, revisando as migrações de banco antes de reverter. Consulte as versões com suporte e seus avisos no [Alpine Linux](https://alpinelinux.org/releases/); a especificação de pacotes [musllinux do PyPA](https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/#musllinux) descreve a compatibilidade dos wheels com musl.
