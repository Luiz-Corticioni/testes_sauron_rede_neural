# 013 — Código por e-mail como alternativa ao TOTP

O pedido de segundo fator no primeiro login é intencional: criar a conta e comprovar
um segundo fator são operações distintas. O aplicativo autenticador permanece válido.
Também é possível confirmar o endereço e autenticar por um código aleatório de seis
dígitos enviado por SMTP configurado pelo operador.

O token é válido por 5 minutos, utilizável uma vez e vinculado à sessão; o banco
armazena apenas um HMAC associado ao usuário, endereço e nonce aleatório. Há intervalo
mínimo de 60 segundos entre envios, limite de 5 envios por janela de 15 minutos e
bloqueio de 15 minutos após 5 tentativas inválidas. A senha atual também é exigida na
verificação; falhas não divulgam qual dado estava incorreto. Não se registra o código
na auditoria. Na criação ou alteração do e-mail, o envio é agendado após o commit.

Uma conta recém-criada com endereço válido deve confirmar o e-mail ou usar TOTP.
Usar TOTP não marca o endereço como comprovado. Administradores, aprovadores e
operadores com permissão de alteração de incidência continuam exigindo segundo fator
a cada sessão e para reautenticação. Contas antigas sem dispositivo preservam o
acesso anterior, salvo perfis que já exigiam MFA. Trocar o endereço invalida a
confirmação anterior e sessões verificadas pelo dispositivo de e-mail.

O Gmail deve ser configurado explicitamente com TLS e senha de aplicativo; nenhuma
credencial de usuário é fornecida pelo sistema. Erro SMTP não equivale a sucesso e
invalida o desafio recém-gerado. Os backups cifrados deixam de incluir sessões e
códigos pendentes, evitando restaurar acesso autenticado ou ressuscitar tokens.

O e-mail depende da segurança e disponibilidade da caixa postal. MFA fortalece o
controle de acesso e não garante sozinho confidencialidade, integridade ou
disponibilidade: auditoria, backups, permissões e operação também são necessários.
Veja [EMAIL_E_MFA.md](../EMAIL_E_MFA.md) para configuração e recuperação.
