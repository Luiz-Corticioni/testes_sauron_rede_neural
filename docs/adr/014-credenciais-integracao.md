# ADR 014 — credenciais de integração limitadas a leitura

**Estado:** implementada em branch de testes; implantação depende de validação.

## Contexto e decisão

Integrações automatizadas precisam consultar inventário sem compartilhar cookies
ou a senha de um usuário. Emitimos um segredo aleatório com identificador público;
armazenamos apenas SHA-256 do segredo completo. A emissão, rotação e revogação
exigem sessão de superusuário com MFA, reautenticação e CSRF. O segredo é entregue
uma única vez; metadados podem ser listados sem recuperar o segredo.

A autenticação `Bearer` é aceita exclusivamente nas duas consultas v1 de ativos
e incidências, com escopos separados `ativos`, `risco` e `incidencias`. O dono
precisa continuar ativo e ser superusuário; escopo não dá acesso a rotas humanas
nem substitui controle de operações sensíveis. A rotação cria e revoga na mesma
transação sob a trava existente. Registros de auditoria não incluem o segredo.

Limites persistentes são 60 consultas por minuto por credencial e 120 tentativas
por minuto por origem, inclusive falhas; a origem é representada por HMAC.
Credenciais e contadores são excluídos dos backups/exportações: após uma
restauração, é necessário emitir novas credenciais, evitando reativar uma antiga
revogação. Sessões e MFA humanos permanecem inalterados.

## Consequências e limites

A limitação por origem pode bloquear clientes que compartilham NAT; o endereço
depende da configuração correta de proxies confiáveis. O controle por banco
acrescenta escrita em cada consulta e deve ser medido antes de uso em alta carga.
O token não é prova de identidade humana e deve ser mantido por cliente em
gerenciador de segredos e transmitido por TLS validado. Não há concessão de
escrita, renovação automática, delegação entre administradores nem integração
com um provedor externo de identidade. Testes locais não comprovam segurança de
configuração de um servidor público.
