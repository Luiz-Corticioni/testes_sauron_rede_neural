# Organização da documentação — 10/11/2026

## O que mudou e por quê

- O README passou a começar pelo objetivo e por caminhos de primeiro acesso. A
  sequência de relatórios históricos no topo dificultava encontrar a instalação,
  a abertura da interface e o login.
- Foram separados os caminhos Windows sem Docker e Docker local, com as portas
  correspondentes, e explicados administrador inicial, senha escolhida, TOTP,
  SMTP e diferença entre a conta do Sauron e a conta do servidor.
- Foi criado `GUIA_DE_USO.md`, com um percurso de cadastro, explicação dos menus,
  interpretação de resultados, operação, backup e resolução de problemas.
- Foi criado `docs/README.md` como índice por público e assunto, incluindo os
  relatórios históricos, registros de arquitetura e evidências. Os documentos
  existentes não foram movidos, para preservar caminhos e links já utilizados.

## Conferências e limites

Os nomes de menus, opções de MFA e comandos foram confrontados com templates e
código atual. Os links locais dos três documentos novos/reorganizados foram
verificados, assim como a presença no índice dos documentos Markdown de primeiro
nível de `docs/`. `manage.py check` e as ajudas dos comandos de cadastro e
provisionamento passaram em ambiente de teste.

Esta revisão altera documentação; não executou todos os fluxos em navegador nem
implantou Docker ou SMTP real. Os relatórios históricos continuam descrevendo o
estado e os resultados das respectivas datas. Os testes Windows e a verificação da
imagem relatados em revisões anteriores devem ser acompanhados no GitHub Actions.
