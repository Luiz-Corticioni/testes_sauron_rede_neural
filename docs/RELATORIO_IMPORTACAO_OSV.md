# Importação offline de resultados OSV-Scanner

## Mudança

A tela de scanner aceita agora o JSON `results` do OSV-Scanner, além do formato Trivy existente. O usuário informa ativo, escopo, origem e data observada com fuso, pois o perfil de JSON aceito não fornece uma data de varredura confiável por si só. A prévia identifica que essa data é declarada e alerta se está no futuro em relação ao servidor.

O parser reconhece identificadores CVE no campo `id` ou em `aliases`, preserva CVE, ecossistema, nome e versão do pacote, e remove duplicatas iguais. O rótulo `ecossistema:nome` codifica `%` e `:` como `%25` e `%3A` nos dois componentes, evitando confundir pares diferentes. Achados sem CVE ou sem os campos de pacote necessários são contados como ignorados; isso inclui GHSA ou outros IDs sem alias CVE. Caminhos de arquivos, descrições e demais dados do relatório não são armazenados. O formato é identificado com `OSV-Scanner:` na origem declarada.

Nenhuma varredura ou conexão externa é executada pelo Sauron. O relatório exige prévia assinada e confirmação com o mesmo arquivo e contexto. A revisão permanece humana e não cria ou altera incidências. Nenhum achado reconhecido não significa segurança, cobertura completa nem ausência de outras falhas. A importação continua vinculada às permissões existentes de scanner e documentos.

## Como usar

1. Obtenha, por procedimento autorizado, um JSON de saída do OSV-Scanner compatível com o formato documentado, de até 2 MB.
2. Em **Scanner offline**, selecione **OSV-Scanner JSON**, o ativo, o escopo e a origem; informe a data da varredura com fuso, por exemplo `2026-11-18T10:30:00-03:00`.
3. Faça a prévia. Confira os achados e a contagem de ignorados; reenvie o mesmo arquivo e contexto em até dez minutos para confirmar.
4. Revise cada achado como aplicável, não aplicável ou inconclusivo, com justificativa. A revisão não altera o inventário automaticamente.

São aceitos até 500 grupos, 5.000 registros de vulnerabilidade, 1.000 aliases por vulnerabilidade e 5.000 achados CVE únicos. Resultados sem nome, versão ou ecossistema não são convertidos; o formato não preserva identificadores exclusivos não CVE, versões corrigidas, caminhos, PURLs ou evidência integral. A revisão não verifica se o pacote está instalado no ativo. O perfil não pretende cobrir todas as variantes ou versões do OSV-Scanner; use a prévia e confira os ignorados.

Testes específicos verificam prévia e confirmação, aliases, deduplicação, dados privados descartados, limitação de entrada, data, permissões e revisão sem criação de incidência. A suíte completa passou com 536 testes Django; após o ajuste dos links na navegação, 26 testes de scanner e interface passaram novamente. Após a correção de rótulos ambíguos, passaram os seis testes OSV e do percurso integrado. Ruff passou. [Formato JSON oficial do OSV-Scanner](https://google.github.io/osv-scanner/output/).
