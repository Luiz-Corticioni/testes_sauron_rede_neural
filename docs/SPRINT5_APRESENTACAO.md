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

## Demonstração das etapas recentes

Use um banco de demonstração isolado. Com uma conta autorizada e MFA concluído, prepare o cenário do [exemplo financeiro](CENARIOS_FINANCEIROS.md), escolhendo dados fictícios. Em **Analisar sensibilidade**, informe uma faixa contendo a premissa original e uma origem; compare os extremos. Para causa compartilhada, cadastre primeiro relações de negócio no mesmo escopo, da origem para os serviços consumidores; informe custos incrementais distintos, justificativas e confirme que não se sobrepõem. Explique que todos os serviços selecionados são afetados pelo mesmo evento e duração: não é uma previsão garantida.

Em **Documentos de componentes → Importar relatório Trivy offline**, escolha um ativo fictício e [trivy-demo.json](exemplos/trivy-demo.json). Informe origem e escopo, confira a prévia e reenvie o arquivo para confirmar. Abra o relatório e registre uma revisão inconclusiva para o achado: ela não cria incidência. O CVE de exemplo é real, mas o pacote e a ligação com o ativo são fictícios.

Em **Sensores de isca**, crie um sensor de demonstração e escolha **Importar Cowrie**. Use [cowrie-demo.jsonl](exemplos/cowrie-demo.jsonl) e um UUID como `a47ac10b-58cc-4372-a567-0e02b2c3d479`; confira a prévia e reenvie o mesmo arquivo. São dois eventos aproveitados e uma linha ignorada. IPs são reservados para documentação e as credenciais de exemplo são fictícias; o adaptador não as grava. A repetição com o mesmo UUID é idempotente se as linhas não forem alteradas.

Esses passos são um roteiro reproduzível, não prova de apresentação ou ensaio realizado. Nunca use os dados de exemplo para afirmar exposição real de um cliente.

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
