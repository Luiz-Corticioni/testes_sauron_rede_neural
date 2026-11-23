# ADR 018 — Observações offline antes de mudanças no inventário

**Estado:** implementado como perfis limitados; implantação real não verificada.

Fontes externas produzem observações `sauron.observacao/1`, preservadas como
registros separados de ativos, incidências e relações. Cada registro contém
origem, tipo, identificadores estáveis, identidade e versão declaradas da fonte,
instantes de observação e recebimento, confiança declarada, erro opcional e
conteúdo minimizado. A confiança é escolhida pelo operador e não é uma medida
estatística. SHA-256 identifica conteúdo; não autentica origem ou veracidade.

O arquivo inteiro é validado antes da gravação; duplicatas idênticas são
idempotentes e um identificador igual com conteúdo diferente cancela o lote.
O lote e seu evento de auditoria compartilham a transação e a trava de escrita.
Uma revisão exige permissão revalidada após a trava. Apenas uma observação de
regra de rede pode gerar uma relação, depois de confirmação humana explícita e
com permissão adicional; essa relação permanece uma evidência declarada, não
uma garantia de tráfego ou caminho de ataque.

Reutilizamos o prazo de revisão e exclusão de relações vencidas, em vez de
inventar um fator de decaimento sem calibração. Uma observação com mais de 90
dias não pode criar relação; a revisão posterior deve ocorrer em até 90 dias.
Se a relação mudar depois da conversão, a interface alerta que a confiança da
observação original precisa ser reavaliada.

Os perfis aceitos são limitados e estritos; não alegam compatibilidade com todas
as versões dos fornecedores. Não são executados scanners, conexões ou comandos.
Os adaptadores dependem apenas da biblioteca padrão do Python e estão desativados
por padrão. Preservamos os importadores Trivy e OSV anteriores.

Falhas de validação ou conflito na interface e no serviço de gravação são
auditadas com uma categoria genérica, sem conteúdo nem credenciais. Observações
aceitas têm `erro` nulo; falhas não são convertidas em fatos de inventário. A
auditoria depende de banco acessível e da confirmação da transação externa;
permissão negada e falhas de infraestrutura podem não gerar esse evento.

Referências consultadas: [estrutura de saída do Grype](https://github.com/anchore/grype/blob/main/templates/html.tmpl),
[exportação de dados do Greenbone](https://docs.greenbone.net/OPENVAS-REPORT-Manual/en/analyzing-data.html)
e [chaves de CSV da Tenable](https://docs.tenable.com/vulnerability-management/Content/Explore/export-findings-csv-keys.htm).
O contrato local não declara conformidade integral com ECS, OCSF ou schemas dos fornecedores.
