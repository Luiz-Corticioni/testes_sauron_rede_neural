# Versão de apresentação sem MFA

[Voltar ao início](../README.md) · [Manual dos recursos](GUIA_DE_USO.md)

## O que mudou e por quê

Esta branch é uma alternativa de contingência para demonstrar a aplicação quando o segundo fator não estiver disponível. O login web e o terminal verificam apenas usuário e senha; não solicitam códigos por e-mail ou por aplicativo, inclusive para administradores. A rota antiga `/mfa/` redireciona para a página inicial. O cadastro de usuário não dispara códigos de acesso por e-mail. Uma faixa na interface identifica a versão e sua limitação.

As tabelas, migrações e partes internas de MFA continuam no código para manter compatibilidade com a estrutura existente: elas não tornam o segundo fator obrigatório nesta branch. Para usar MFA, utilize a branch `main` e sua documentação. Esta versão de apresentação é menos protegida contra o roubo de senhas: use contas e dados de teste, em rede local controlada.

Permanecem as permissões por usuário, senha, proteção CSRF, registro de auditoria e prazo de sessão. No terminal, ações de escrita podem pedir a senha novamente. A senha não é um segundo fator. Um usuário comum continua sem acesso à administração e a ações que não estejam autorizadas para sua conta.

## Começar a apresentação

1. Siga as instruções do [README](../README.md) para baixar esta branch e iniciar o Sauron por Python ou Docker. As duas opções usam bancos separados se configuradas em instalações separadas.
2. Crie o primeiro administrador no banco da demonstração usando o comando indicado no README. Escolha a senha quando solicitada; não há senha padrão. Se o banco já possuir superusuário, use uma conta existente.
3. Acesse o endereço indicado no README. Entre com o usuário e a senha. Nenhum código adicional será pedido.
4. No painel de administração, crie contas de teste e atribua somente as permissões necessárias. Para verificar a diferença de acesso, saia e entre com uma conta comum.
5. Consulte o [manual](GUIA_DE_USO.md) para navegar pelos ativos, vulnerabilidades, mapas e relatórios. As referências daquele manual à obrigatoriedade de MFA aplicam-se à `main`, não a esta branch.

Para terminal em instalação Python local: `python manage.py sauron_cli`. Entre com usuário e senha. Confirme os comandos disponíveis com `python manage.py help`. Não compartilhe senhas ou arquivos `.env`.

## Docker e isolamento

O README usa o nome explícito `sauron-apresentacao`, que cria volumes independentes dos projetos Compose com outros nomes. A porta local 2228 precisa estar livre: se outra instalação estiver usando essa porta, pare-a antes. O comando `down` sem `-v` preserva o banco da demonstração; o parâmetro `-v` apaga volumes do projeto e não é necessário para encerrá-lo. Não aponte esta branch para o banco ou volume de produção. Não habilite o proxy público.

## Limites da verificação

Os testes automatizados desta branch incluem o acesso de administrador e de usuário comum, senha inválida, CSRF, ausência de envio automático de códigos e uso do terminal. **30 testes legados são explicitamente marcados como ignorados** porque pressupõem o MFA da `main`; alguns também continham outras verificações, portanto a cobertura desta branch não é equivalente à da versão principal. Os demais testes continuam sendo executados. Consulte o resultado da execução de testes e do GitHub Actions antes da apresentação; um teste automatizado não substitui uma apresentação de ensaio no computador e banco que serão usados.
