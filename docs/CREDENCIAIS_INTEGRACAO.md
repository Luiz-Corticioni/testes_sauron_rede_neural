# Credenciais para integração de leitura

As credenciais servem para programas consultarem a API v1 sem manter uma sessão
humana. Não são JWT e não dão acesso à interface, à documentação protegida, a
escritas ou a operações administrativas. As permissões e o estado ativo do
administrador proprietário continuam sendo conferidos a cada uso.

## Criar, usar e encerrar

1. Um superusuário com sessão, MFA e reautenticação recente faz `POST` em
   `/api/v1/credenciais/`, com CSRF válido e corpo JSON como
   `{"escopos":["ativos"],"dias":7}`. A duração aceita é de 1 a 90 dias.
2. A resposta `201` contém `id`, `escopos`, `expira_em` e `segredo`. O segredo
   aparece somente nessa resposta: guarde-o em um gerenciador de segredos do
   cliente e não o registre em arquivos de código, logs ou histórico de comandos.
   A consulta `GET /api/v1/credenciais/` lista os metadados do administrador,
   sem segredos, em páginas de até 50 itens.
3. Envie-o somente por HTTPS no cabeçalho `Authorization: Bearer <segredo>`.
   O escopo `ativos` permite a listagem normal; `risco` permite a listagem
   ordenada por risco; `incidencias` permite consultar ativos afetados por uma
   vulnerabilidade. Um escopo não implica os demais.
4. Para substituir a credencial, o mesmo superusuário, autenticado com MFA e
   reautenticação recente, envia `POST` com `{"dias":7}` para
   `/api/v1/credenciais/<id>/rotacionar/`. A anterior é revogada na mesma
   transação que cria a nova. Guarde o novo segredo apresentado uma única vez.
5. Para revogar, envie `POST` com `{}` para
   `/api/v1/credenciais/<id>/revogar/`. A desativação ou perda do papel de
   superusuário do proprietário também impede o uso. Um administrador só pode
   gerenciar as próprias credenciais; se a conta proprietária estiver comprometida,
   outro administrador deve desativá-la para interromper todos os seus tokens.

Para gerenciamento por cliente HTTP, obtenha e envie o cookie e o cabeçalho CSRF
da sessão Django. O documento [OpenAPI](openapi-v1.json) descreve os corpos e
respostas. Uma chamada de integração com credencial inválida ou revogada recebe
401; escopo insuficiente recebe 403; excesso de requisições recebe 429.

## Limites e auditoria

O servidor guarda somente o hash SHA-256 de um segredo aleatório. O limite é de
60 consultas por minuto por credencial e 120 tentativas por minuto por endereço
de origem, incluindo tokens inválidos; o endereço é representado por HMAC. Esses
contadores usam o banco compartilhado, portanto instâncias devem usar o mesmo
banco. Proxies devem estar corretamente configurados como confiáveis. O limite
por origem pode afetar clientes que compartilham um NAT e precisa ser avaliado
antes de uso em escala; não substitui proteção na borda da rede.

Criação, uso, revogação e tentativa inválida são registrados sem o segredo. As
credenciais e os contadores ficam fora de backups e exportações: uma restauração
exige emitir novas credenciais e não reativa uma credencial antiga. Guarde e
proteja separadamente as chaves do ambiente. Para transporte, configure TLS e
confira o certificado; o teste HTTP local não comprova a configuração do servidor.
