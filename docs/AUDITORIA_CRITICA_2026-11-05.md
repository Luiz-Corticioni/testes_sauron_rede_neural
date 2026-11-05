# Auditoria crítica — 05/11/2026

## Julgamento

O Sauron é um protótipo de inventário e análise que já reúne controles úteis. Isso não o torna automaticamente uma plataforma pronta para uma operação SOC: dados ausentes, hipóteses não calibradas, concorrência e infraestrutura podem invalidar conclusões ou interromper o serviço. A quantidade de módulos, métricas ou gráficos não é evidência de maturidade. Resultados financeiros e caminhos de grafo precisam continuar acompanhados de fonte, escopo, premissas e revisão humana.

Esta revisão examinou o código e os testes disponíveis, com foco em autenticação, autorização, integridade dos dados, disponibilidade das simulações e limitações do modelo. Não é pentest completo nem certificação de produção.

## Falhas corrigidas

1. **Autorização na reconciliação de documentos.** A permissão era verificada antes da espera pela trava de escrita. Se fosse revogada nessa espera, a operação poderia prosseguir com uma decisão antiga. O serviço agora consulta a conta e as permissões novamente depois da trava, antes de gravar. O teste de regressão simula a revogação nesse intervalo.

2. **Contenção durante MFA.** As verificações de senha por e-mail e TOTP executavam o hash custoso enquanto mantinham a trava global de escrita. Tentativas concorrentes poderiam atrasar gravações sem relação com o login. O hash foi movido para antes da trava; dentro da transação o sistema reconfirma conta ativa e hash de senha, recusando o acesso se a senha tiver mudado. Testes simulam a troca entre a verificação e a trava. Isso reduz o tempo segurando a trava, sem eliminar o custo da verificação de senha ou certificar resistência a ataques distribuídos. A [OWASP recomenda controles de autenticação e limitação de tentativas](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html).

3. **Integridade no Django Admin.** A administração de vulnerabilidades podia salvar identificadores que o domínio rejeita e uma nota CVSS 3.1 divergente do vetor. Isso podia interromper o cálculo de risco ou apresentar severidade incorreta. O formulário agora rejeita IDs incompatíveis com a categoria, recalcula a nota pelo vetor válido e mantém o identificador existente somente para leitura. A gravação passa pelo mesmo serviço dos demais cadastros. Testes exercitam o formulário administrativo, o recálculo e a proteção do ID.

4. **Concorrência de simulações financeiras.** Existia limite por requisição, mas requisições com parâmetros diferentes podiam contorná-lo em conjunto e multiplicar o uso de memória/CPU. Agora há no máximo duas simulações Monte Carlo simultâneas por diretório de dados compartilhado no mesmo host; resultados já presentes no cache não ocupam vaga. Excesso recebe HTTP 429 e orientação para tentar novamente. As travas são liberadas em falhas e pelo sistema operacional quando um processo termina. Há testes da API, de exceção e de processos independentes no Windows. O limite não coordena hosts com diretórios de dados diferentes e não dimensiona, por si só, o servidor de produção.

## O que continua inadequado ou não comprovado

- **Financeiro:** o laboratório continua usando EPSS global e fatores de cenário como hipótese de simulação. Isso não mede a probabilidade de comprometimento ou de perda financeira de um ativo específico; os custos padrão não foram calibrados. P95 é percentil dos cenários gerados, não garantia de confiança sobre perdas reais. A [FIRST define EPSS para exploração observada de uma CVE em 30 dias](https://www.first.org/epss/). Para decisão financeira, o próximo passo é calibrar entradas e validar resultados com dados reais, não acrescentar casas decimais ou estender o horizonte.
- **Rede de propagação:** caminhos do grafo representam relações cadastradas. Eles não demonstram acesso efetivo, exploração, pré-condições ou comprometimento; inventário incompleto produz análise incompleta. São necessárias evidências atualizadas e validação com responsáveis pelos ativos.
- **Registros legados:** identificadores de vulnerabilidade fora do padrão precisam de saneamento controlado. O Admin agora impede editar a identidade e não aceita novas gravações incompatíveis; não foi feita uma migração automática que pudesse quebrar vínculos existentes.
- **MFA por e-mail:** foi habilitado para administradores por solicitação anterior. A segurança desse segundo fator depende também da caixa de e-mail e do processo de recuperação. TOTP continua disponível. A entrega SMTP a Gmail/UFU reais ainda depende de uma conta de envio autorizada e não foi comprovada nesta auditoria.
- **Infraestrutura:** SQLite/WAL foi usado em testes locais anteriores. Não houve homologação de concorrência e recuperação em PostgreSQL, TLS/proxy reais, SMTP real ou armazenamento compartilhado em múltiplos hosts. A trava das simulações exige que os processos usem o mesmo diretório de dados e um sistema de arquivos que respeite travas locais.
- **Cache de arquivos:** o backend do Django serializa objetos no diretório de cache; ele deve ser protegido contra gravação por usuários ou serviços não confiáveis. Não foi realizada auditoria de ACL do servidor real.
- **Capacidade:** o teste anterior de 100 usuários foi um ensaio curto e sintético. Ele não comprova capacidade contínua para inventários grandes, centenas de importações ou tráfego distribuído. O novo limite financeiro requer dimensionamento conforme memória e número de workers da implantação.
- **Dependências:** a consulta pontual com `pip-audit --no-deps` cobre as versões diretas listadas, não todas as transitivas, ferramentas de desenvolvimento, sistema operacional ou imagem. Os resultados dependem da base consultada na data da execução.

## Validação

**380 testes passaram** na suíte completa, incluindo oito testes novos para os problemas identificados. Ruff, Bandit, verificação sintética de configuração de produção e `makemigrations --check --dry-run` passaram. O `pip-audit` não encontrou vulnerabilidades conhecidas nas dependências diretas consultadas, dentro do escopo limitado descrito acima. O smoke test com `DEBUG=0` verificou TOTP, CSRF, EPSS simulado, SSVC, SBOM/VEX, relações, cobertura, simulação financeira e cache. A proteção de concorrência foi exercitada por processos independentes no Windows, incluindo término de processo e liberação da vaga.

Os testes são automatizados com banco e dados sintéticos. O teste entre processos usa diretório temporário próprio. As correções não alteram esquema de banco; nenhuma credencial ou dado real é necessário para executá-los.

## Aplicação

Faça backup da instalação, atualize os arquivos, execute `python manage.py preparar_servidor` e reinicie web e agendador. Não há nova migração. Em caso de resposta 429 na simulação, aguarde e tente novamente; cenários diferentes não devem ser disparados em massa para contornar o limite.
