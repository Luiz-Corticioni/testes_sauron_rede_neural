# Sugestão de apresentação do Sauron

[← Sprint 5](SPRINT5_RASTREABILIDADE.md) · [Manual de uso](GUIA_DE_USO.md)

Este é um roteiro proposto de cinco minutos; ajuste ao tempo do professor. Não é evidência de ensaio, gravação ou apresentação realizada. Prepare previamente uma instalação de demonstração com dados fictícios, a autenticação configurada e o serviço de e-mail/autenticador testado. Nunca revele senhas, códigos MFA, `.env`, chaves ou dados reais.

1. **Problema (40 s):** mostrar como ativos, vulnerabilidades e dependências ajudam a identificar prioridades, sem sugerir que o Sauron descobre automaticamente todo o ambiente.
2. **Inventário (60 s):** abrir um ativo fictício, sua sala, responsável e incidências; explicar que uma CVE só afeta o ativo quando existe evidência de aplicabilidade.
3. **Risco (60 s):** mostrar CVSS, EPSS/KEV disponíveis e o modelo de relações. Explicar que pontos de risco não são probabilidades e dados ausentes não são risco zero.
4. **Financeiro (60 s):** mostrar um cenário hipotético de 30 dias; explicar que Monte Carlo apresenta resultados condicionados às hipóteses informadas, não previsão garantida de perda.
5. **Segurança e limitações (60 s):** mostrar controle de acesso, MFA e auditoria; esclarecer que a imagem está sujeita a scan e que implantação real/24 horas exigem evidência.
6. **Perguntas (20 s):** abrir para dúvidas.

Plano alternativo: ensaiar o roteiro em uma instalação reserva e gravar uma demonstração sem dados reais. A gravação e o ensaio ainda precisam ser feitos; não afirmar que foram produzidos.

## Perguntas possíveis

1. **O Sauron é antivírus?** Não: ajuda a inventariar, relacionar e priorizar informações; não impede diretamente todo ataque.
2. **CVSS é probabilidade de ataque?** Não. É uma medida padronizada de severidade; EPSS estima outra dimensão.
3. **EPSS prevê se a minha empresa será atacada?** Não. É uma estimativa geral vinculada à CVE, que precisa de contexto local.
4. **O cálculo financeiro garante o prejuízo?** Não. É um cenário de 30 dias condicionado às entradas e à modelagem.
5. **Um usuário comum administra contas?** Os perfis padrão não concedem essa administração; o acesso é conferido no servidor.
6. **Como funciona o segundo fator?** A sessão exige verificação por TOTP ou e-mail conforme a configuração disponível; e-mail depende de SMTP funcional.
7. **Posso perder os dados ao recriar container?** O volume preserva dados quando usado corretamente, mas não substitui backups testados.
8. **O sistema está provado seguro?** Não. Testes e análises reduzem incerteza; a imagem e o servidor precisam de revisão contínua.
9. **Por que Django?** O projeto já usa suas sessões, formulários, ORM e migrações; trocar de framework não garante qualidade e amplia o trabalho.
10. **O Sauron está funcionando 24 horas no servidor da faculdade?** Isso só pode ser afirmado depois de uma execução real com evidências.
