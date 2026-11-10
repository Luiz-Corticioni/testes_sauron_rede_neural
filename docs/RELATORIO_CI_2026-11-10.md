# Correção do GitHub Actions — 10/11/2026

O workflow falhava na validação antes de iniciar os testes: `runner.temp` estava
em `jobs.validacao.env`, onde o contexto `runner` não está disponível. Isso não
significa que os testes da aplicação tenham falhado; eles não chegaram a começar.

O diretório temporário agora é definido por uma etapa, onde `runner.temp` é
permitido, e gravado em `GITHUB_ENV` para as etapas seguintes. Validamos o arquivo
com actionlint e executamos localmente o comando de configuração com um caminho
contendo espaços. A confirmação do resultado completo depende da execução real
no GitHub Actions; uma correção de sintaxe não garante que todas as etapas passem.

Referência: [contextos permitidos por posição no workflow](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability).
