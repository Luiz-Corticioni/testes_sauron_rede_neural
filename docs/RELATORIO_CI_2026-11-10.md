# Correção do GitHub Actions — 10/11/2026

O workflow falhava na validação antes de iniciar os testes: `runner.temp` estava
em `jobs.validacao.env`, onde o contexto `runner` não está disponível. Isso não
significa que os testes da aplicação tenham falhado; eles não chegaram a começar.

O diretório temporário agora é definido por uma etapa, onde `runner.temp` é
permitido, e gravado em `GITHUB_ENV` para as etapas seguintes. Validamos o arquivo
com actionlint e executamos localmente o comando de configuração com um caminho
contendo espaços. A confirmação do resultado completo depende da execução real
no GitHub Actions; uma correção de sintaxe não garante que todas as etapas passem.

Após a correção, a execução começou e os registros mostraram que `runuser` não
estava instalado na imagem Fedora. A instalação explícita de `util-linux` e `grep`
garante as ferramentas necessárias ao teste como usuário comum.

Os testes também revelaram dois problemas em sua própria configuração: um teste
EPSS era bloqueado pela variável de ambiente do CI apesar de usar resposta simulada;
dois testes dependiam de `requests`, que não é dependência da aplicação. O primeiro
passou a liberar a rotina apenas no escopo do mock; os outros passaram a bloquear
conexões de socket diretamente. Nenhuma chamada à internet é liberada pelos testes.

Referência: [contextos permitidos por posição no workflow](https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability).
