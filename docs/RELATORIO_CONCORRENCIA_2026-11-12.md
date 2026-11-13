# Relatório: proteção contra edição concorrente — 12/11/2026

[Início](../README.md)

## Problema observado

Na CI Windows, dois testes detectaram que uma edição antiga de perímetro ou relação podia ser aceita depois de outra alteração. Os serviços comparavam a versão enviada no formulário com `atualizado_em`, mas duas gravações consecutivas podiam receber exatamente o mesmo horário. Nesse caso, o valor antigo ainda parecia atual e a comparação não detectava o conflito. A causa foi reproduzida localmente de maneira determinística com o relógio congelado; os dois testes falharam antes da correção.

## O que mudou e por quê

- As datas `atualizado_em` de `PerimetroRelacoes` e `RelacaoAtivos` usam um campo que, durante a gravação sob a trava transacional já existente, compara a hora atual com a versão salva do mesmo registro. Quando o relógio não avança ou retrocede, a nova versão recebe um microssegundo a mais que a versão anterior. Assim, a edição antiga é rejeitada e o formulário pode informar que deve ser recarregado.
- O formato da versão e o fluxo de permissões, validação e auditoria continuam os mesmos. Uma versão atual ainda pode ser editada; em caso de conflito a alteração anterior é preservada. O avanço mínimo pode representar um instante ligeiramente posterior ao relógio: é um identificador de versão, não prova de precisão temporal de microssegundos.
- A migração `0028` atualiza somente o estado dos campos no Django. O tipo das colunas não muda e, no SQLite verificado, a migração não executa operações SQL sobre as tabelas. Instalações existentes devem seguir o processo normal de atualização com backup e serviços parados. A alteração evita que novas edições antigas sejam aceitas; não recupera automaticamente dados sobrescritos antes da correção.
- Os testes existentes agora reproduzem a colisão de horário, além de verificarem os dados preservados. Foram acrescentados testes para relógio retrocedendo, sucessivas versões atuais, alterações parciais e os dois formulários web com versão antiga.

A rejeição de versões antigas ocorre nos serviços usados pelas telas e pelo terminal. Uma gravação por `save()` faz a versão avançar, mas uma chamada direta a `save()` não compara por si só a versão que o usuário abriu. Alterações feitas diretamente no banco ou com `QuerySet.update()` também contornam `save()`, validações e sinais; não devem ser usadas como alternativa para editar esses registros. A configuração normal usa uma única conexão `default`. PostgreSQL e acesso simultâneo em múltiplos servidores não foram exercitados nesta máquina.

## Verificações

- Os dois testes apontados falharam com relógio congelado antes da correção e passaram após ela.
- Os testes das áreas de relações e cobertura, incluindo o fluxo web, foram executados em SQLite isolado.
- `makemigrations --check` não encontrou mudanças adicionais; `sqlmigrate` confirmou que a migração 0028 é somente de estado no SQLite.
- Uma cópia local descartável com dados fictícios de perímetro e relação foi atualizada pelo instalador após backup cifrado. A migração foi aplicada e os vínculos, dados e cadeia de auditoria foram preservados.
- Nessa cópia SQLite, duas threads tentaram editar o mesmo perímetro usando a mesma versão e, em seguida, fizeram o mesmo com uma relação, com relógio congelado. Em cada caso, uma gravação ocorreu e a outra recebeu `ValidationError`. É um ensaio pontual, não um teste de carga ou validação de PostgreSQL.
- A suíte Django completa passou no Windows local: 398 testes. Os 6 testes de pytest, 12 testes JavaScript e o teste do painel financeiro também passaram.
- A CI do GitHub deve ser verificada para o commit publicado; os testes locais não comprovam, por si só, o resultado no runner remoto.
