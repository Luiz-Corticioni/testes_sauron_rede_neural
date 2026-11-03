> Registro histórico: a alternativa de código por e-mail foi adicionada posteriormente; veja [ADR 013](013-mfa-email.md).

# 006 — MFA obrigatório e recuperação local

Staff e usuários com permissões de aprovação/linha de base exigem TOTP.
Não há matrícula por senha na web: operador local provisiona por
`python manage.py provisionar_mfa --usuario NOME` e entrega a URI por canal seguro.
O dispositivo só é confirmado após código válido. URI/chave nunca entra na auditoria.
Recuperação exige procedimento local autenticado, revisão de identidade e remoção
administrativa do dispositivo; não existe bypass por e-mail ou código fixo.
Web exige senha+TOTP novamente após 5 minutos para POSTs privilegiados (mais estrito
que somente aceite/linha de base). Sessões expiram em 30 min de inatividade ou 8 h
absolutas por padrão; CLI aplica os mesmos relógios nas operações de menu.
Comandos de gestão são acesso privilegiado ao servidor; não são uma API pública.
