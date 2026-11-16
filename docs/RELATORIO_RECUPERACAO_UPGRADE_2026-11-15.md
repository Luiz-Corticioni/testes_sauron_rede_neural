# Atualização e recuperação em ambiente isolado

O ensaio revelou duas falhas. Primeiro, o backup com o código novo recusava bancos anteriores às migrações 0030 a 0034 por não reconhecer as tabelas ainda não criadas. Agora ele permite a ausência somente quando a migração correspondente ainda não foi aplicada; se ela já foi aplicada, a tabela ausente continua causando falha.

Segundo, a carga de grupos e permissões durante a restauração gerava registros extras de auditoria antes de carregar a cadeia original. Isso causava conflito com os gatilhos de imutabilidade. A carga agora é executada em processo separado e somente em banco SQLite temporário de restauração; nesse processo os sinais de auditoria de alterações de associações são desconectados durante a carga e reconectados depois. Os gatilhos não são removidos. A cadeia carregada continua sendo verificada antes da publicação do banco, e o banco original nunca é sobrescrito.

## Ensaio realizado

Em volume Docker separado e sem rede, a imagem Debian anterior criou dados fictícios, usuário administrador e dispositivo TOTP, com esquema até a migração 0033. A imagem nova criou um backup cifrado antes da atualização e o restaurou em outro arquivo. Foram conferidos senha do usuário fictício, presença do dispositivo TOTP, quatro ativos e seis incidências. A atualização do banco antigo aplicou a migração 0034 e concluiu a preparação. A primeira tentativa de restauração falhou de forma segura e levou à correção descrita acima.

Os testes automatizados cobrem restauração com grupo e permissão, preservação da cadeia e exclusão de sessões, recusa de banco existente, chave incorreta, ausência de tabelas pré-migração e falha quando a migração já consta como aplicada. O ensaio não comprova recuperação em servidor externo ou a disponibilidade da chave e do backup de uma instalação real. É necessário preservar separadamente o backup e as chaves Fernet e HMAC da auditoria; dados fictícios não são dados de produção.
