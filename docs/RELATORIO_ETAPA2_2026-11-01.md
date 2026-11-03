# Relatório de implementação — etapa 2 — 01/11/2026

## O que foi implementado

Esta etapa continua a revisão anterior. A aplicação completa mantém as correções de MFA, papéis e recuperação da primeira entrega e recebe as mudanças abaixo. Este relatório complementa o relatório anterior; em caso de conflito sobre o limitador de login e as permissões do terminal, vale esta etapa.

| Problema | Mudança | Por que foi feita |
|---|---|---|
| Contadores de login dependiam de cache e travas em arquivos locais | Modelo técnico `LimiteLogin`, migração `0021` e serviço transacional compartilhado pelo banco | Cache limpo, reinício do processo ou outro worker não reiniciam os limites. Instâncias com o mesmo PostgreSQL passam a compartilhar as reservas de autenticação. |
| Tentativas simultâneas podiam ser admitidas antes de registrar falha | Reserva persistida antes da autenticação | Tentativas em andamento entram no limite de cinco por par de conta/origem. Processos que falham não apagam a reserva. A janela expira em quinze minutos. |
| Lock durante senha ou atraso prejudicaria disponibilidade | Transação curta; senha e espera executadas depois de liberar a trava | Evita manter o banco bloqueado durante o cálculo caro da senha ou o atraso progressivo. A trava compartilhada existente serializa apenas as alterações de estado. |
| Resposta antiga poderia limpar uma janela nova | Conclusão confere a expiração da reserva antes de limpar o contador | Autenticação que termina após a expiração não remove o limite criado em outra janela. |
| CLI não compartilhava os limites da web | Terminal usa o mesmo serviço e contador por nome de conta | Aplica limitação persistente ao canal terminal, com origem local separada e contagem global por nome compartilhada. |
| Possível corrida de TOTP no terminal SQLite | Trava transacional antes da verificação TOTP | Alinha o terminal ao caminho web e impede que dois verificadores usem simultaneamente o mesmo estado de dispositivo sem serialização. |
| Dados efêmeros de login entrariam em backups | Exclusão de `LimiteLogin` da exportação lógica de backup | Não restaura reservas antigas nem exige que essa nova tabela exista antes do backup de atualização. A estrutura continua criada pelas migrações. |
| Usuário com cadastro de ativos podia gerar backup de toda a aplicação | Backup completo no terminal exige superusuário | Permissão de inventário não autoriza exportar contas e dispositivos contidos no backup cifrado. |
| Usuário que alterava vulnerabilidades podia executar todas as rotinas | Rotinas globais no terminal exigem superusuário | Tarefas alteram estados, decisões, snapshots e âncoras além de um cadastro específico. |
| Carga de demonstração disponível com permissão de cadastro | Carga demonstrativa pelo menu restrita a superusuário | Evita introduzir dados artificiais no inventário por usuário comum. Não execute seed sobre dados reais. |
| Compose PostgreSQL publicava porta em todas as interfaces | Publicação alterada para `127.0.0.1:8000:8000` | Mantém a mesma restrição adotada no Compose principal. |
| Pré-requisitos de produção dependiam apenas de documentação | Comando `verificar_implantacao [--json]` | Detecta configuração insegura, migrações pendentes, chave de backup inválida, proxy sem CIDRs e destinos de backup/âncora ausentes ou internos. Falhas produzem código de saída não zero. |
| Novo teste de CLI deixou ator de auditoria no contexto do teste seguinte | Fixture limpa o ator antes e após cada teste | Evita contaminação entre contas descartáveis e erros de chave estrangeira dependentes da ordem da suíte. A falha foi observada na execução integrada e corrigida antes da entrega. |

O contador grava hashes de conta/origem, contagem, lista limitada de hashes por origem e expiração; não grava senha ou nome fornecido em texto claro. Esses hashes ainda são dados técnicos potencialmente correlacionáveis. Não equivalem a anonimização garantida.

## Comportamento do limitador

- Até cinco reservas por par conta/origem, por janela de quinze minutos. Tentativas em curso contam antes de se saber o resultado.
- Origem que acumula vinte contas distintas é bloqueada. O contador global por nome mantém atraso progressivo, sem bloqueio global rígido da conta, reduzindo o risco de bloqueio distribuído por terceiros.
- Sucesso limpa o par e retira a conta da lista da origem; falha ou interrupção mantém a reserva até sua expiração. Requisições bloqueadas não prolongam a janela.
- Reservas expiradas são removidas em chamadas futuras. Não existe fallback para cache local quando o banco falha; o caminho de autenticação depende do banco estar disponível.
- SQLite permanece apropriado a um host. O protocolo transacional usa a mesma trava de escrita/advisory lock da aplicação. A execução real entre hosts/PostgreSQL continua pendente de homologação.

## Atualização e uso

1. Pare web e agendador. Faça backup cifrado com a versão instalada e preserve `.env`, dados e chaves.
2. Extraia esta entrega em pasta nova e instale as dependências do projeto.
3. Execute `python manage.py preparar_servidor`. Alternativamente, aplique `python manage.py migrate` e publique os estáticos conforme o procedimento existente. A migração **0021** é obrigatória antes de iniciar o código novo.
4. Preserve o TOTP já provisionado. Primeiro acesso e recuperação continuam descritos em `EMAIL_E_MFA.md`.
5. Para avaliar a configuração real, execute `python manage.py verificar_implantacao --json`. Uma configuração local de desenvolvimento deve reprovar os requisitos de produção; isso não impede desenvolvimento local.
6. Configure destinos candidatos para `SAURON_BACKUP_DESTINO_ADICIONAL` e `SAURON_AUDIT_ANCHOR_PATH` fora de `DATA_DIR`, com diretórios existentes. Confirme a independência real, permissões, retenção, custódia de chaves e restauração por procedimento operacional. Um caminho diferente no mesmo disco não é independência física.

O verificador não envia e-mails, não publica a aplicação e não cria serviços externos. A aprovação de suas checagens locais não é uma certificação de infraestrutura ou segurança.

## Validação

**Suíte final: 194 testes, zero falhas, em 65,563 segundos.** Foram acrescentados 11 testes aos 183 da entrega anterior. Ruff e Bandit aprovados; Bandit sem ocorrências.

A evidência final acompanha este pacote em `evidencias/etapa2/`.

- Teste concorrente com oito processos independentes e um banco SQLite em arquivo: cinco reservas aceitas e três recusadas, sem erro de banco.
- Testes cobrem limite persistente entre clientes com cache limpo, expiração, resposta antiga, spraying, sucesso/falha, bloqueio no terminal, privilégios para backup/rotinas e verificador de implantação.
- Smoke com `DEBUG=0`, banco descartável, TOTP, cookies seguros, HTTPS simulado e estáticos WhiteNoise repetido nesta etapa. Verificador de implantação aprovado com configuração sintética completa, sem certificar os diretórios sintéticos como cópias externas reais.
- Ruff, Bandit, compatibilidade de dependências, ausência de migrações de modelo pendentes, check Django de produção e coleta de estáticos são registrados nas evidências.
- A tentativa de `pip-audit` foi interrompida porque o ambiente não resolveu `pypi.org`. Não foi possível consultar a base atualizada de vulnerabilidades; ausência de achados não foi presumida. O CI já contém `pip-audit` e deve executá-lo em ambiente com conectividade.

## Julgamento crítico e pendências

Persistir limites no banco elimina uma dependência local da autenticação, mas não transforma o projeto inteiro em uma aplicação distribuída homologada: rotinas, arquivos, caches e agendador ainda exigem uma topologia coerente. Não publique réplicas independentes como se toda a aplicação tivesse sido validada entre hosts.

TOTP segue sujeito a phishing. WebAuthn/SSO não foi adicionado nesta etapa. SMTP real, PostgreSQL real, proxy TLS, instaladores Linux e armazenamento externo ainda precisam de homologação no ambiente do operador. Não há credenciais nem infraestrutura desse ambiente no material recebido.

CVSS, similaridade, propagação e Monte Carlo continuam sujeitos às hipóteses documentadas. Não há histórico real rotulado que permita calibrar probabilidades ou validar previsões financeiras. Esta revisão não inventou dados para alegar tal comprovação.

A entrega constitui uma nova base funcional testada para homologação. Os pontos operacionais acima continuam sendo condições para uma liberação responsável em produção.
