# Correção do primeiro acesso e do código por e-mail

**Data:** 05/11/2026.

O erro relatado, “TOTP obrigatório; provisione o autenticador no servidor”, vinha da política do próprio Sauron para contas privilegiadas. O primeiro administrador já podia ser criado localmente, mas, ao entrar no terminal, a aplicação rejeitava a opção de e-mail. O fluxo foi alterado para aceitar código por e-mail cadastrado ou TOTP também para administradores, tanto na web quanto no terminal. A conta continua exigindo senha e um segundo fator; um código não cria sessão sozinho.

O envio usa o endereço cadastrado na conta como destinatário. Endereços válidos `@gmail.com` e `@ufu.br` são aceitos; não foi criada uma restrição que exclua outros domínios válidos. O endereço do destinatário não precisa ser igual ao do remetente SMTP.

Após falha de envio, o código não é aceito e o bloqueio de um minuto para reenvio é removido, permitindo nova tentativa após corrigir a configuração. O limite por janela de envios permanece ativo. Ao promover uma conta que se autenticou por e-mail, a sessão precisa verificar o segundo fator novamente.

## Primeiro administrador

No diretório da instalação, depois de preparar o banco, execute como usuário com acesso de escrita aos arquivos da aplicação:

```sh
python manage.py cadastrar_administrador --usuario admin --email seu_endereco@ufu.br
```

O comando pede senha e confirmação; não exige login de um administrador anterior nem uma conta de administrador do sistema operacional. Ele recusa criar outro primeiro administrador se já houver superusuário, inclusive inativo. Se a conta já foi criada, não repita o cadastro: ajuste o e-mail com `python manage.py definir_email_usuario --usuario admin --email seu_endereco@ufu.br`.

Em servidor remoto ou diretório/banco protegido, é necessário ter acesso autorizado e permissão de escrita para executar comandos e gravar a conta. A aplicação não consegue conceder ao usuário permissões que o sistema operacional ou o administrador do servidor não concedeu.

## Configuração para enviar mensagens reais

O Sauron precisa de um serviço SMTP autorizado. O e-mail do destinatário, por si só, não fornece esse serviço. Uma opção para demonstração é uma conta Gmail pessoal que permita senha de aplicativo; conforme a [ajuda do Google](https://support.google.com/accounts/answer/185833), a conta precisa ter verificação em duas etapas, e a opção pode não estar disponível em contas institucionais. Outra opção é um provedor SMTP autorizado pela organização.

No `.env` privado da instalação, preencha os parâmetros documentados em [e-mail e MFA](EMAIL_E_MFA.md), incluindo `SAURON_EMAIL_ENABLED=1`, host, porta, usuário, senha de aplicativo e remetente. Não compartilhe credenciais no repositório ou no chat. Reinicie o Sauron após a alteração. O mesmo remetente autorizado pode enviar mensagens a Gmail e UFU, sujeito às regras do provedor e à entrega da caixa destinatária.

Teste primeiro a configuração com `python manage.py diagnosticar_email`. Para testar a entrega real, execute `python manage.py diagnosticar_email --enviar-para SEU_EMAIL`, com um endereço seu, e confira a caixa de entrada e spam. Aceitação pelo SMTP não comprova entrega final.

## Verificação e limites

**372 testes aprovados** na suíte completa; Ruff e Bandit passaram. Os novos testes cobrem código para Gmail e UFU, administrador na web e no terminal, reenvio após falha e revogação de sessão em promoção. As integrações SMTP reais não foram exercitadas.

Os testes de Gmail e UFU usam o backend de e-mail em memória, sem credenciais reais, e exercitam geração, destinatário, código e login. Eles não comprovam entrega pela internet. Não foi recebido acesso a uma conta SMTP autorizada nesta sessão; portanto, não foi possível configurar credenciais nem confirmar uma mensagem entregue em Gmail ou UFU reais.

O uso de e-mail para administradores atende ao novo requisito, mas a proteção passa a depender também da segurança da caixa de e-mail e de sua recuperação. O autenticador TOTP continua disponível como alternativa. Documentos de fases anteriores registram a política vigente na época; o guia de e-mail e este relatório descrevem a política atual.
