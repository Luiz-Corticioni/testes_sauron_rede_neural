# CI e imagem Docker — 15/11/2026

> Registro da imagem Debian anterior. A alternativa posterior e suas limitações estão no [relatório Alpine](RELATORIO_IMAGEM_ALPINE_2026-11-15.md).

O [workflow 43776288296](https://github.com/Luiz-Corticioni/testes_sauron_rede_neural/actions/runs/43776288296), do commit `3086358`, terminou com falha no Trivy. As validações Linux e Windows, as instalações Ubuntu, Fedora, Rocky Linux e Windows passaram; o job de imagem chegou à varredura e falhou nela. Isso não comprova o resultado dos commits posteriores.

A imagem com as mudanças até `1369e92` foi reconstruída sem cache com a base fixada no Dockerfile e as atualizações Debian disponíveis. O Trivy 0.76.2, com base atualizada em 16/11 UTC (15/11 no horário local), encontrou **47 combinações HIGH, nenhuma CRITICAL e 11 CVEs distintos**, sem versão corrigida indicada. São os mesmos identificadores e pacotes já discutidos em [análise detalhada](RELATORIO_ANALISE_CVES_DOCKER_2026-11-15.md). O resultado é temporal e não prova ausência de outras falhas. O CI continua bloqueando HIGH/CRITICAL; não foram ocultados achados nem instalados pacotes de outra distribuição.

Em volume isolado, a preparação aplicou todas as migrações, inclusive `0033`, e compilou os templates. A aplicação respondeu HTTP 200 em `/api/saude/`; depois de reiniciar o container, a migração continuou aplicada no volume e a rota respondeu 200. Este teste não demonstra resiliência, 24 horas de disponibilidade nem uso real da aplicação.

A suíte Django local passou 476 testes e o Ruff passou no projeto. A verificação da imagem em outro sistema e a execução no GitHub para os novos commits continuam necessárias; a base Debian deve ser monitorada e a imagem reconstruída quando houver correções. A lista de medidas de redução de exposição e limitações permanece no relatório detalhado.
