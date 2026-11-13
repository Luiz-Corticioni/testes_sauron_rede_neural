# Sensores de isca — fase 1

[← Documentação](README.md) · [Exemplo fictício](exemplos/honeypot-eventos.json)

## Objetivo e limites

O Sauron cadastra sensores e importa **manualmente** um formato próprio e minimizado de eventos. Esta fase **não instala Cowrie**, não simula SSH, não abre portas, não recebe eventos automaticamente e não confirma que ocorreu um ataque. O formato abaixo não é o formato nativo do Cowrie; um adaptador, autenticação de origem e testes de entrega seriam necessários antes de uma integração real.

Sensores são marcados como demonstração ou operacionais; o padrão é demonstração. Após importar o primeiro evento, o ambiente e o ativo vinculado não podem ser alterados pela aplicação: crie outro sensor para outro contexto. O rótulo depende da informação do operador e não comprova que a origem é genuína. Uma interação isolada pode ser teste, varredura ou ação maliciosa; ausência de eventos não demonstra ausência de ataques. A fase não calcula CVSS, EPSS, probabilidade de invasão nem altera incidências ou risco.

## Preparação e teste passo a passo

1. Para atualizar uma instalação existente, faça backup usando o procedimento de [implantação](IMPLANTACAO.md), preserve a chave e interrompa os serviços antes da migração. Instale as dependências e execute `python manage.py preparar_servidor`. A migração 0029 cria as tabelas novas.
2. Entre na interface com uma conta autorizada e conclua o MFA. O grupo Gerentes recebe as permissões do recurso quando os grupos são configurados; Operadores e Auditores não recebem leitura do sensor ou dos eventos por padrão. Permissões individuais podem ser concedidas conscientemente por administrador.
3. No menu **Sensores de isca**, escolha **Cadastrar sensor**. Informe nome, localização, responsável, eventual ativo e mantenha o ambiente **Demonstração** para ensaios. Cadastrar não inicia serviço algum.
4. Na tabela, selecione **Importar JSON** e escolha `docs/exemplos/honeypot-eventos.json` na sua cópia do projeto. Os endereços do exemplo pertencem à faixa reservada para documentação e não são observações reais.
5. Confira os dois registros e o alerta agrupado. Reimporte o arquivo para testar a idempotência: nenhum evento novo deve ser criado. O alerta também aparece em **Alertas e decisões** para quem tiver as permissões exigidas nessa tela.
6. Para parar importações de um sensor, use **Editar** e desabilite-o. Os eventos existentes permanecem.

## Contrato do arquivo

O arquivo é um array JSON UTF-8 de 1 a 500 objetos e no máximo 1 MiB. Cada objeto tem exatamente quatro campos textuais:

```json
[
  {
    "id": "demo-001",
    "observado_em": "2026-11-13T12:00:00Z",
    "origem_ip": "192.0.2.10",
    "tipo": "CONEXAO"
  }
]
```

O `id` é fornecido por quem prepara o arquivo e deve ser estável e único para o sensor, com até 100 letras ASCII, dígitos ou `_.:-`. O horário precisa incluir fuso; o Sauron também grava o horário de recebimento. O tipo é `CONEXAO`, `LOGIN_FALHOU`, `LOGIN_ACEITO` ou `OUTRO`; “aceito” é o comportamento relatado pela isca, não prova de comprometimento de ativo real.

Campos extras, incluindo senha, usuário e comando, são rejeitados em vez de armazenados. Uma repetição idêntica é ignorada; a reutilização do mesmo ID com conteúdo diferente rejeita o lote inteiro. A importação e seus alertas acontecem na mesma transação. O sistema agrupa novos eventos por sensor e dia UTC, usando o mecanismo existente de supressão de alertas; depois de reconhecido, um alerta pode permanecer suprimido pelo período configurado. Não há processamento automático ou envio de notificações externas nesta fase.

## Privacidade e operação

O IP de origem é armazenado para investigação e pode ser dado pessoal. A leitura requer permissões de sensor, evento e ativo; o acesso administrativo deve ser restrito. O backup lógico cifrado inclui esses registros. Esta fase **não implementa expiração automática, anonimização, exclusão seletiva ou encaminhamento a SIEM**; defina política de retenção antes de importar dados reais. A auditoria registra quem criou ou editou sensor e quem importou um lote, além de contagens, sem registrar os IPs do lote nessa entrada de auditoria.

Antes de ligar uma isca real, obtenha autorização, use isolamento de rede e regras de saída adequadas, planeje a coleta e revise riscos do sensor. Nunca instale sensores ou abra portas no servidor compartilhado sem autorização. A integração futura deve validar limites, autenticidade, duplicação, atraso e perda de eventos; conteúdo recebido nunca deve ser executado.

## Verificações realizadas

Os testes automatizados cobrem MFA e permissões, importação pela interface, formatos inválidos e campos extras, duplicatas, conflito de ID com rollback, alertas por dia, ambiente, desativação e ausência de alteração nas incidências. Foi exercitado backup antes da migração 0029 e aplicação posterior em banco SQLite descartável, sem dados reais. O estado da suíte e da CI deve ser conferido no relatório da alteração e no commit publicado.

## Relatório desta implementação — 13/11/2026

- Foram criados os modelos de sensor e evento, para preservar identificação, rótulo de demonstração, proveniência e observação separados do inventário de vulnerabilidades.
- A importação manual limita tamanho e campos, verifica IP/data, recusa segredos, detecta duplicatas e grava o lote de forma atômica. O alerta agrupa interações por sensor e dia para reduzir ruído; não atribui culpa nem altera modelos de risco.
- A interface permite cadastrar, editar, desabilitar e consultar sensores e eventos. A classificação e o ativo associado são preservados após a primeira importação para não reclassificar dados antigos.
- Permissões explícitas protegem a leitura e a escrita; auditoria registra autoria e contagens. O backup antes de atualizar reconhece que as novas tabelas ainda não existem antes da migração.
- A suíte Django completa passou com 429 testes antes de dois testes adicionais de interface e backup. Em seguida, os 14 testes específicos do módulo passaram. A suíte pytest teve 6 sucessos, e 12 cenários JavaScript passaram. Ruff e Bandit foram executados; o Bandit mostrou um aviso preexistente de `nosec` no backup. `makemigrations --check` não identificou alterações pendentes.
- A CI da branch permanece sujeita à verificação da imagem Docker: o scan anterior identificou vulnerabilidades altas mesmo após a atualização da base. Nenhum teste desta fase comprova coleta real, operação 24 horas ou segurança de um servidor externo.
