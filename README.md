> Trabalho 2: veja a [matriz de requisitos e resultados](docs/RELATORIO_TRABALHO_2.md) e o [guia Docker](docs/DOCKER_TRABALHO_2.md). A execução no servidor por 24 horas ainda precisa de evidência real.

> Auditoria de 05/11/2026: [achados, correções e limitações](docs/AUDITORIA_CRITICA_2026-11-05.md). Permissões são revalidadas na reconciliação, a verificação de senha do MFA não mantém a trava de escrita, o Admin valida CVSS/identidade e simulações financeiras têm limite de concorrência.

> Política atual: contas comuns e administrativas podem usar código enviado ao e-mail cadastrado ou TOTP. Configure uma conta SMTP autorizada conforme [e-mail e MFA](docs/EMAIL_E_MFA.md); o remetente pode enviar a endereços Gmail e UFU. A criação do primeiro administrador é local e dispensa uma sessão administrativa existente.

> Fase 7: [carga de 100 usuários, cache e primeiro administrador](docs/RELATORIO_FASE7_CARGA_CACHE.md). Resumos do painel são reutilizados por até 15s; risco e cenários financeiros evitam reconstruções duplicadas. `preparar_servidor` pré-carrega as análises. Foram testadas 100 sessões com 4 administradores e 96 leitores. Rajadas de login pelo mesmo IP continuam limitadas. Sem nova migração além de 0026.

> Fase 6: [acesso, cenários de 30 dias e orientação de uso](docs/RELATORIO_FASE6_CONSOLIDACAO.md). A simulação financeira usa 30 dias, exige EPSS recente com origem e explicita suas hipóteses. Atualize o EPSS na própria tela ou no terminal. Nove tarefas receberam exemplos e próximos passos; o guia traz roteiros por responsabilidade. Autorizações são revalidadas nas escritas compartilhadas. Sem nova migração além da 0026: execute `python manage.py preparar_servidor` e reinicie web/agendador. Consumidores externos devem atualizar o contrato da API financeira. Relatórios anteriores são históricos.

> Fase 5 de evolução: [qualidade e cobertura das evidências](docs/RELATORIO_FASE5_COBERTURA.md). Aplique a migração 0026 com `python manage.py preparar_servidor`. Acesse Relações por camada → Qualidade ou o acesso no Modo Euler; no terminal, menu operacional 9 → 5. Declare o perímetro antes de medir cobertura. Revisões são históricas, têm evidência e validade máxima de 90 dias após a observação. Operadores podem registrar revisões; Gerentes também administram perímetros. Um perímetro declarado limita os grafos do escopo de mesmo nome.

> Fase 4 de evolução: [grafo de relações por camada](docs/RELATORIO_FASE4_RELACOES.md). Aplique a migração 0025 com `python manage.py preparar_servidor` (também atualiza os grupos oficiais). Acesse Relações por camada → Analisar, o novo acesso no Modo Euler ou a opção 9 do menu operacional. Relações de rede, identidade e negócio exigem escopo, evidência e prazo de revisão. Cálculos são estruturais e não confirmam exploração.

> Fase 3 de evolução: [componentes, SBOM e VEX com proveniência](docs/RELATORIO_FASE3_COMPONENTES.md). Atualize com `python -m pip install -r requirements.txt` e aplique a migração 0024 com `python manage.py preparar_servidor`. Acesse Software → SBOM/VEX ou a opção 8 do menu operacional no terminal. Importações são declarações, exigem conferência e não encerram incidências automaticamente.

> Fase 2 de evolução: [SSVC Deployer por ocorrência](docs/RELATORIO_FASE2_SSVC.md). Aplique a migração 0023 com `python manage.py preparar_servidor`. Acesse Incidências → SSVC ou a opção 5 do menu de incidências no terminal.

> Fase 1 de evolução: [EPSS com histórico e proveniência](docs/RELATORIO_FASE1_EPSS.md). Aplique a migração 0022 com `python manage.py preparar_servidor`; sincronize explicitamente com `python manage.py sync_epss`.

> Etapa 2 de segurança: leia [o relatório mais recente](docs/RELATORIO_ETAPA2_2026-11-01.md). Aplique a migração 0021 antes de iniciar. O comando `python manage.py verificar_implantacao --json` verifica pré-requisitos locais de produção.

> Revisão de segurança 01/11/2026: leia [o relatório histórico](docs/RELATORIO_REVISAO_2026-11-01.md) e [a política atual de MFA](docs/EMAIL_E_MFA.md) antes de instalar ou atualizar. Documentos anteriores são históricos.

# Sauron Apogeu

O Sauron é uma aplicação de inventário e gestão de vulnerabilidades para apoiar a equipe de segurança e os responsáveis pelos ativos na identificação, análise e priorização de riscos de uma infraestrutura. Seu objetivo é reunir informações sobre equipamentos, softwares, vulnerabilidades e dependências em um só lugar, permitindo que decisões de tratamento sejam acompanhadas e auditadas.

O projeto oferece uma interface web e uma interface de terminal. Foi desenvolvido também como projeto de estudo: modelos matemáticos e decisões de arquitetura são documentados para que seus resultados possam ser examinados e discutidos. Ele apoia a análise humana; suas recomendações não comprovam, por si só, que um ativo é vulnerável ou que uma falha foi explorada.

## O que o sistema faz

- **Inventário:** cadastra e organiza ativos, softwares e suas relações, incluindo dependências entre equipamentos.
- **Vulnerabilidades e incidências:** registra vulnerabilidades e sua ocorrência em cada ativo, mantendo o estado e as evidências do tratamento.
- **CVE e fontes externas:** consulta informações públicas da NVD e indicadores como o catálogo KEV. KEV é a lista da CISA de vulnerabilidades conhecidas por terem sido exploradas; sua presença é um sinal para priorização, não uma prova de comprometimento do seu ambiente. A disponibilidade e os dados dependem das fontes externas.
- **CVSS:** calcula a nota base CVSS 3.1 a partir das métricas informadas e permite compará-la com uma nota CVSS 4.0 publicada na NVD quando disponível. As versões usam métricas diferentes: uma diferença entre notas não é, isoladamente, um erro de cálculo. O comando `manage.py auditar_cvss` confere notas cadastradas sem alterá-las.
- **Risco e priorização:** combina severidade, incidências e dependências por um modelo matricial para estimar propagação e apoiar a avaliação de impacto. O resultado depende da qualidade do inventário e das premissas; não é uma previsão garantida.
- **Decisões e acompanhamento:** registra ações, justificativas e evidências, com controles de permissão e auditoria; rotinas periódicas ajudam no acompanhamento de prazos e alertas.
- **Proteção de acesso e dados:** oferece autenticação em duas etapas por aplicativo autenticador ou código por e-mail, registros de auditoria e backups cifrados. Essas medidas contribuem para a segurança, mas não garantem sozinhas confidencialidade, integridade e disponibilidade.

## Instalação e primeiro acesso

Escolha o guia do seu sistema operacional:

- [Instalação e atualização no Windows](docs/INSTALACAO_WINDOWS.md)
- [Instalação e atualização no Fedora/RHEL](docs/INSTALACAO_LINUX.md)

Após preparar a instalação e aplicar as migrações, crie o primeiro administrador no terminal, na pasta que contém `manage.py`:

```sh
python manage.py cadastrar_administrador --usuario admin --email seu_endereco@gmail.com
```

O comando solicita senha e confirmação. Esse primeiro cadastro não exige sessão, MFA, e-mail ou SMTP prévios e não inicia uma sessão. Ele recusa a criação se já existir um superusuário, inclusive inativo. O e-mail é opcional com `--email`.

Para entrar, configure o SMTP e solicite o código na tela de MFA ou no terminal. Como alternativa, provisione um autenticador TOTP para a conta criada:

```sh
python manage.py provisionar_mfa --usuario admin
```

Registre a URI em um aplicativo autenticador caso escolha TOTP e proteja esse segredo. O e-mail depende de uma conta SMTP de envio autorizada; ter um destinatário Gmail ou UFU não configura o remetente automaticamente. Consulte o [guia de e-mail e MFA](docs/EMAIL_E_MFA.md). Para uso além do computador local, consulte [implantação](docs/IMPLANTACAO.md).

## Como usar

1. Cadastre equipamentos e softwares e mantenha suas relações e dependências atualizadas.
2. Registre ou consulte vulnerabilidades e vincule as ocorrências aos ativos afetados. Revise os indícios e as informações das fontes antes de tomar decisões.
3. Consulte severidade, CVSS, KEV e resultados de risco para priorizar o trabalho conforme o contexto da organização.
4. Registre responsáveis, decisões e evidências de tratamento; acompanhe prazos e alertas. O agendador deve permanecer em execução para as rotinas periódicas.

O **Guia rápido** da interface explica conceitos e ações. Para detalhes sobre a comparação, veja [CVSS](docs/COMPARACAO_CVSS.md); para a arquitetura e os cálculos, consulte [arquitetura](docs/ARQUITETURA.md) e [explicação técnica](docs/EXPLICACAO_SAURON.md).

## Arquivos e dependências

- `requirements.txt`: versões usadas para instalar a aplicação.
- `requirements.in`: arquivo de entrada para regenerar a lista de dependências; hoje seu conteúdo é igual ao de `requirements.txt`, mas sua finalidade é distinta. Não é necessário instalá-lo para executar o Sauron.
- `requirements-dev.txt`: ferramentas opcionais de testes, análise e manutenção; não é necessário para o uso normal.
- `inventario/`, `sauron_web/`, `manage.py` e `scripts/`: código da aplicação e ferramentas operacionais. Os arquivos de migração preservam o histórico necessário para criar ou atualizar o banco.
- `tests/`, `.github/` e documentos de revisão/ADRs: testes, integração contínua e histórico técnico; não são necessários para a operação cotidiana, mas são úteis para manutenção e verificação.
- `.env`, banco de dados, chaves e backups são dados locais: mantenha-os protegidos e não os publique. O pacote distribuído não inclui esses dados.

## Validação e limitações

Os testes automatizados podem ser executados com `python manage.py test`; as instruções para ferramentas adicionais estão em [validação](docs/VALIDACAO.md). A análise crítica e suas limitações estão em [revisão crítica](docs/REVISAO_CRITICA.md). O modelo de risco depende de dados e parâmetros fornecidos; módulos experimentais descritos na documentação não devem ser tratados como previsão operacional. A disponibilidade de integrações externas depende de rede e das respectivas fontes.
