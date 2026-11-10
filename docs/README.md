# Documentação do Sauron

> Nesta branch, o MFA está desativado. Comece pelo [guia da apresentação](APRESENTACAO_SEM_MFA.md);
> documentos históricos podem descrever a política de MFA da branch `main`.

[← Voltar ao README](../README.md) · [Manual de uso](GUIA_DE_USO.md)

Este é o ponto de entrada para os documentos do projeto. Os guias de uso ajudam a
executar a versão atual; os relatórios registram decisões, testes e limitações da data
em que foram escritos. Eles não são um certificado de que um servidor está seguro.

## Começar e operar

| Necessidade | Documento |
|---|---|
| Abrir no Windows, preparar banco, atualizar e iniciar o agendador | [Instalação Windows](INSTALACAO_WINDOWS.md) |
| Instalar e atualizar em Fedora/RHEL | [Instalação Linux](INSTALACAO_LINUX.md) |
| Aprender o fluxo de telas e cada grupo de recursos | [Manual de uso](GUIA_DE_USO.md) |
| Entender funções e limitações em linguagem simples | [Guia simples](GUIA_SIMPLES_REANALISE_2026-11-10.md) |
| Criar conta inicial, configurar SMTP/TOTP e recuperar acesso | [E-mail e MFA](EMAIL_E_MFA.md) |
| Entender CVSS 3.1 e comparação com 4.0 | [Comparação CVSS](COMPARACAO_CVSS.md) |
| Executar com Docker, HTTPS e reunir evidências de 24 horas | [Docker para o trabalho](DOCKER_TRABALHO_2.md) |
| Configurar servidor, atualização, backups e diagnóstico | [Implantação](IMPLANTACAO.md) |

Dentro da interface web, o menu **Guia rápido** oferece uma orientação resumida para
responsáveis pelo negócio, analistas e responsáveis pelo inventário. Acesso a dados
e ações depende das permissões de cada conta.

## Para compreender e avaliar

- [Explicação técnica do projeto](EXPLICACAO_SAURON.md): domínio, relações e cálculo.
- [Arquitetura atual](ARQUITETURA.md): camadas, serviços e pontos de integração.
- [Conteúdos aplicados](CONTEUDOS_APLICADOS.md): exemplos didáticos e reconstrução JSON.
- [Requisitos e rastreabilidade do Trabalho 2](RELATORIO_TRABALHO_2.md): itens
  presentes, parciais e pendentes, incluindo roteiro de apresentação.
- [Validação reproduzível](VALIDACAO.md): testes, carga e verificações disponíveis.
- [Índice automático de arquivos](INVENTARIO_ARQUIVOS_2026-11-10.md): localização
  dos arquivos versionados no início da reanálise; não é leitura manual integral.
- [Exemplos de SBOM, VEX e roteiros](exemplos/): material didático; não representa
  dados observados da sua organização.

## Histórico de evolução por recurso

Estes relatórios explicam o que mudou e por quê. Informações sobre o que ainda seria
implementado ou números de testes referem-se à data de cada fase; confira o manual
e o relatório mais recente para a situação atual.

1. [Fase 1 — EPSS e histórico](RELATORIO_FASE1_EPSS.md).
2. [Fase 2 — SSVC por incidência](RELATORIO_FASE2_SSVC.md).
3. [Fase 3 — componentes, SBOM e VEX](RELATORIO_FASE3_COMPONENTES.md).
4. [Fase 4 — relações por camada](RELATORIO_FASE4_RELACOES.md).
5. [Fase 5 — qualidade e cobertura](RELATORIO_FASE5_COBERTURA.md).
6. [Fase 6 — acesso e cenários de 30 dias](RELATORIO_FASE6_CONSOLIDACAO.md).
7. [Fase 7 — carga, cache e administrador inicial](RELATORIO_FASE7_CARGA_CACHE.md).

## Revisões, segurança e limitações

- [Organização da documentação, 10/11/2026](RELATORIO_DOCUMENTACAO_2026-11-10.md).
- [Reanálise de 10/11/2026](RELATORIO_REANALISE_2026-11-10.md).
- [Correção do CI em 10/11/2026](RELATORIO_CI_2026-11-10.md): histórico da correção
  inicial; confira também a execução mais recente do GitHub Actions para o estado atual.
- [MFA e servidor externo, 06/11/2026](RELATORIO_MFA_SERVIDOR_2026-11-06.md).
- [Auditoria crítica, 05/11/2026](AUDITORIA_CRITICA_2026-11-05.md).
- [Correção de e-mail, 05/11/2026](RELATORIO_CORRECAO_EMAIL_2026-11-05.md).
- [Revisão de segurança, 01/11/2026](RELATORIO_REVISAO_2026-11-01.md) e
  [etapa 2](RELATORIO_ETAPA2_2026-11-01.md).
- [Revisão crítica](REVISAO_CRITICA.md), [remediações](REMEDIACAO.md) e
  [análise comparativa](ANALISE_COMPARATIVA.md), mantidas como registros históricos.
- [Evidências registradas por fase](evidencias/): resultados daquela execução, não
  garantia de funcionamento do seu ambiente.

## Decisões de arquitetura

Os documentos abaixo são registros de decisões; alguns abordam possibilidades de
integração futura. A existência de uma proposta não significa que ela esteja ativa.

| Assunto | Registro |
|---|---|
| Componente afetado e matching | [001](adr/001-componente-afetado.md) · [003](adr/003-matching-deterministico.md) |
| Decisões humanas | [002](adr/002-decisoes-humanas.md) |
| Risco esparso e pesos | [004](adr/004-risco-esparso.md) · [008](adr/008-pesos-e-unidades.md) |
| Auditoria, retenção e backups | [005](adr/005-auditoria-e-retencao.md) · [007](adr/007-banco-backups.md) |
| MFA, recuperação e e-mail | [006](adr/006-mfa-e-recuperacao.md) · [013](adr/013-mfa-email.md) |
| Telemetria e sistema imune | [009](adr/009-telemetria.md) · [010](adr/010-imunologia-comportamental.md) |
| Automação reversível e EPSS/SSVC | [011](adr/011-soar-reversivel.md) · [012](adr/012-epss-ssvc-purple-team.md) |

Para contribuir, leia a [arquitetura](ARQUITETURA.md), rode os testes indicados em
[validação](VALIDACAO.md) e documente mudanças e limitações em um relatório próprio.
