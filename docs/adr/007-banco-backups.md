# 007 — Banco configurável e backups cifrados

DATABASE_URL aceita SQLite/PostgreSQL; SQLite continua padrão. PRAGMAs e INSERT OR
IGNORE ficam isolados por vendor; PostgreSQL usa trava transacional advisory.
O pacote não acrescenta psycopg à lista de dependências autorizadas: a alternativa
compose.postgres.yaml exige imagem do operador com driver compatível com Django.
PostgreSQL não foi executado neste ambiente. Planeje migração em cópia, migre esquema
limpo, importe dados em janela controlada e verifique contagens/chaves/auditoria.
Nenhum dado é migrado automaticamente ao mudar a configuração.

Backup lógico Fernet inclui auth, MFA e auditoria com microssegundos completos.
Sessões expiradas são excluídas da cópia; originais permanecem no banco.
SAURON_BACKUP_KEY é obrigatória para backup/restauração. Guarde-a fora do volume,
separada dos arquivos; perda da chave impede restauração. Destino adicional pode
apontar fora do volume. O token já está cifrado em repouso e continua cifrado
durante transferência; use também TLS/SSH no transporte.
Hashes de senha e segredos TOTP estão dentro do token cifrado. O banco operacional
SQLite/PostgreSQL ainda exige criptografia de disco/volume e TLS externo.
A restauração explicitamente cria SQLite novo, preserva originais e exige troca
manual de configuração após validação. Para PostgreSQL, faça importação operacional
ensaiada: o comando desta rodada não sobrescreve um servidor PostgreSQL.
JSON e Fernet são processados em memória; dimensione memória pelo tamanho do banco.
