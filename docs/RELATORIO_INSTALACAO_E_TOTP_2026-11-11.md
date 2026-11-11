# Relatório — instalação e autenticação (11/11/2026)

[Início](../README.md) · [Linux](INSTALACAO_LINUX.md) · [Windows](INSTALACAO_WINDOWS.md) · [Login e TOTP](EMAIL_E_MFA.md)

## Problema e alterações

- O instalador Linux exigia seleção de Fedora/RHEL e tentava instalar pacotes mesmo se Python 3.12 já estivesse pronto. Agora detecta Python 3.12 com `venv`, `ensurepip`, SSL e SQLite e dispensa sudo nesse caso. Acrescenta seleção de pacotes para Ubuntu 24.04. Para outras distribuições, a instalação funciona com Python 3.12 compatível previamente instalado; a disponibilidade de wheels, arquitetura e dependências continua sendo requisito.
- Acrescentado `instalar_windows.ps1`: cria ambiente isolado, instala dependências, verifica conflitos e usa a mesma preparação de banco e auditoria do Linux. Reexecução preserva `.env` e banco; atualização com migrações pendentes exige opção explícita e backup cifrado.
- O comando de provisionamento TOTP agora exibe uma chave Base32 para entrada manual no aplicativo, além da URI existente. Ambas são segredos. O dispositivo continua sendo confirmado somente após código válido; não foi enfraquecida a exigência de MFA.
- Os guias incluem o endereço exato para obter o código, conferência dos arquivos, cadastro manual no autenticador e comando opcional `seed_demo` para preencher somente um inventário de teste vazio. Clone não restaura o banco pessoal de outra máquina.
- Acrescentados testes de login real com a chave apresentada e testes simulados do instalador. A CI ganhou verificações específicas de instalação Ubuntu e Windows; sua presença não comprova que tenham passado.

## Evidências e limites

- Um clone público da `main` foi realizado em diretório separado; os arquivos `manage.py`, `requirements.txt`, `instalar_linux.sh` e o modelo CSV estavam presentes.
- Windows: instalação nova real em cópia isolada, incluindo download de dependências, preparação, estáticos e verificação; reexecução e diagnóstico concluídos com `.env` preservado. O cenário de demonstração criou quatro ativos, cinco vulnerabilidades e três dependências na cópia de teste.
- Teste automatizado do provisionamento converte a chave exibida em código TOTP, efetua login com senha e CSRF e confirma o acesso. Os 28 testes focados de MFA, instalação e permissões passaram; a suíte Django completa passou com 390 testes na execução local. Ruff e verificação sintática do instalador também passaram.
- O teste Bash usa sistema/Python simulados. Nesta máquina não havia distribuição WSL nem Docker disponível para reproduzir diretamente a instalação no Fedora relatada. Uma execução pública anterior da CI concluiu os jobs de instalação Fedora e Rocky, mas o job de testes Windows falhou; isso não determina a causa da falha relatada pelo usuário.
- Não foi fornecida mensagem de erro para o download no Fedora; portanto sua causa específica permanece desconhecida. Consulte a saída exata do `git clone`, da instalação ou do pip caso se repita. Sem rede, pacotes e wheels instaláveis, não é possível garantir instalação em qualquer sistema ou arquitetura.
