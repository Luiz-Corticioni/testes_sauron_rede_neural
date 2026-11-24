# Fase 5 — conectores e observações offline

**Atualização de 24/11/2026:** esta descrição registra o estado da fase em
22/11. A política de retenção de observações foi implementada depois; consulte o
[relatório de correções](RELATORIO_PENDENCIAS_2026-11-24.md) para o estado atual.

## O que mudou e por quê

Foi acrescentada uma fila de observações `sauron.observacao/1` para registrar
procedência sem converter automaticamente arquivos externos em fatos do
inventário. O contrato expõe origem/formato, tipo, fonte e versão declaradas,
identificador, data observada, data recebida, confiança declarada, campo de erro,
SHA-256 e campos minimizados. A API de leitura autenticada é
`GET /api/observacoes/<id>/`. O contrato e as decisões estão no [ADR 018](adr/018-observacoes-offline.md).

As importações são **desativadas por padrão** e executadas somente com arquivo
local enviado por usuário autorizado. Nenhum adaptador executa scanner ou
contata fornecedores. O formulário oferece prévia; a confirmação exige reenviar
o mesmo arquivo e contexto com token assinado de até dez minutos. CSV ou JSON
malformado, chave JSON duplicada, conflitos e limites excedidos são recusados
sem observações parciais. Reenvio idêntico não duplica registros; alterar o
conteúdo de uma identidade para o mesmo instante gera conflito. Falhas de
arquivo/contexto no formulário e erros de validação ou conflito no serviço de
gravação geram auditoria genérica, sem armazenar o arquivo ou o conteúdo do erro.
Permissão negada, banco indisponível ou rollback de transação externa podem
impedir esse registro. A prévia direta em serviço retorna erros sem gravá-los.

O identificador da observação é derivado da chave do registro e do instante
declarado, dentro do formato e da identidade de fonte. Versão de fonte e confiança
fazem parte da verificação de conteúdo. Um novo instante é uma nova observação;
não altere artificialmente a data para contornar conflitos. O mesmo ativo
importado por formatos ou fontes diferentes pode gerar observações distintas;
não há reconciliação automática entre elas.

O usuário pode revisar observações como válidas, incorretas ou inconclusivas,
sem alterar incidências ou cadastros. Apenas regras de rede podem, após revisão
explícita e com permissões adicionais, criar `RelacaoAtivos`. Não se convertem
regras de negação em relações. Regras `allow` não consideram prioridade, rotas,
NAT, outras regras ou tráfego efetivo. A relação é uma declaração sujeita a
revisão, não prova de conectividade. Uma observação com mais de 90 dias não pode
criar uma relação; o novo prazo de revisão deve estar entre amanhã e 90 dias.
Relações vencidas já ficam fora da análise. A confiança e a idade da observação
original aparecem a quem tem permissão; alterações posteriores da relação são
sinalizadas. Para marcar uma observação como incorreta ou inconclusiva após criar
relação, revogue a relação vinculada primeiro.

## Perfis aceitos

Os perfis abaixo são recortes deliberados, não suportam todas as exportações e
versões dos fornecedores. Limite: 2 MiB e 5.000 registros/achados; Trivy também
limita grupos a 500. Arquivos são UTF-8, aceitando BOM. Não são mantidos arquivos
originais nem campos de descrição de plugin, comando, URL ou outros campos
desconhecidos. Valores escolhidos ainda precisam de revisão para não conter dados
sensíveis; o hash do alvo não é uma técnica de anonimização. Um JSON
ou CSV sintaticamente válido ainda pode ser uma exportação incompleta; resultado
vazio nunca comprova ausência de falhas.

| Formato | Campos usados e limites |
|---|---|
| Trivy JSON | `SchemaVersion: 2`, `Results`, `Vulnerabilities`, `VulnerabilityID`, `PkgName`, `InstalledVersion`. Só IDs CVE diretos; o `Target` é representado por hash, não pelo texto original. |
| Grype JSON | `matches[].vulnerability.id` e `matches[].artifact.name/version`. Só IDs CVE diretos; identificadores sem CVE, inclusive aliases indiretos, são ignorados. |
| OpenVAS CSV | Cabeçalhos `IP,Port,Port Protocol,NVT OID,CVEs`; `Severity` é opcional e declarada. CVEs separadas por vírgula, ponto e vírgula ou espaço. |
| Nessus CSV | Cabeçalhos `Host,Port,Protocol,Plugin ID,CVE`; `Risk` é opcional e declarada. CVEs separadas por vírgula, ponto e vírgula ou espaço. |
| GLPI CSV | Cabeçalhos exatos `ID,Name,Type`; apenas ID, nome e tipo são preservados. |
| GLPI JSON | Lista de objetos com `id`, `name` e `itemtype`; apenas esses campos são preservados. |
| Firewall JSON | Perfil local abaixo; IDs devem ser IDs de ativos Sauron, não CIDRs, curingas ou nomes resolvidos automaticamente. |

Em Trivy, dois registros para o mesmo alvo/CVE/pacote com versões diferentes
no mesmo arquivo são tratados como conflito; no Grype, o mesmo ocorre para a
mesma CVE/pacote. Separe os resultados se precisar revisar versões distintas.
IDs sem CVE reconhecível são ignorados e contabilizados. CSV precisa ter todas
as colunas obrigatórias e ao menos uma linha. Não se importam planilhas, XML,
portas em faixa nem dados que exijam resolução automática de identidades.

Exemplo fictício do perfil **local** de regras, sem credenciais:

```json
{
  "rules": [
    {"id": "regra-1", "acao": "allow", "origem_ativo": "ID-SAU-1",
     "destino_ativo": "ID-SAU-2", "escopo": "Rede demonstrativa",
     "protocolo": "tcp", "porta": 443}
  ]
}
```

São aceitos `tcp`/`udp` com porta de 1 a 65535 ou `icmp` com porta 0; `deny` é
contabilizada como ignorada. Não se conclui que uma regra permita tráfego apenas
por aparecer na exportação. Os IDs precisam existir para criar a relação após
revisão. Esse JSON é um contrato do Sauron, não exportação nativa universal de
qualquer fornecedor de firewall ou nuvem.

## Habilitar e usar

1. Faça backup e aplique a migração `0044` com `python manage.py migrate` no
   ambiente da aplicação. Para Docker, reconstrua a imagem e siga a preparação
   do Compose documentada no projeto.
2. Em `.env`, configure `SAURON_IMPORTACAO_OBSERVACOES_ENABLED=1` e reinicie a
   aplicação. Sem isso, a tela informa que a importação está desativada e o
   serviço recusa gravações. A configuração não habilita acesso à rede.
3. Conceda somente as permissões necessárias de observação e revisão. Importar
   exige leitura da observação/revisão e `add_observacaoimportada`; revisar exige
   `add_revisaoobservacao`; criar relação também exige leitura de ativos e
   relações e `add_relacaoativos`. Operadores e auditores não recebem leitura
   dessas observações por padrão. O comando `configurar_grupos` substitui as
   permissões dos grupos padrão; revise o impacto em permissões personalizadas.
4. Abra **Observações → Importar arquivo**, informe fonte sem URL/e-mail,
   versão, data com fuso e confiança declarada. Confira a prévia e reenvie o
   mesmo arquivo para confirmar. A idade depende da data declarada pelo operador;
   o conteúdo do arquivo não comprova o relógio ou a fonte.
5. Na fila, revise cada observação. Para regra de rede, selecione criar relação
   somente depois de verificar origem, destino, escopo e evidência. Registre
   justificativa e prazo. A interface mostra a procedência, mas o grafo continua
   sendo uma representação estrutural declarada.

IPs, nomes de host e descrições escolhidas podem ser sensíveis. A visualização é
restrita por permissões e as respostas novas usam `Cache-Control: no-store`;
isso não criptografa o banco. **Ainda não existe retenção ou exclusão automática
para essas observações e revisões**: defina política de acesso, retenção e
descarte antes de importar dados reais. O backup do banco inclui as tabelas; a
exportação JSON resumida de inventário não as inclui. A confiança não altera
automaticamente pesos matemáticos nem constitui uma probabilidade.

## Verificação e limites

Os testes usam apenas fixtures sintéticas, sem rede. Foram exercitados os sete
perfis, duplicatas, conflitos, truncamento, limites, prévia, CSRF, permissões,
rollback da relação e auditoria. Dois testes de concorrência passaram em um
PostgreSQL 16 descartável, isolado sem rede: importações idênticas simultâneas
e promoção simultânea da mesma observação. A primeira tentativa do segundo
teste falhou pela configuração somente leitura do diretório de dados; após mudar
o diretório temporário para `/tmp`, ambos passaram. O banco foi encerrado.

No contêiner Linux isolado, `python manage.py test --noinput` executou 612
testes com sucesso, com seis testes ignorados; os dois testes novos específicos
de concorrência PostgreSQL foram executados separadamente, como acima. A suíte
emitiu um `FutureWarning` de SciPy em `inventario/matematica/risco.py`, que
merece acompanhamento na próxima atualização dessa dependência. Não houve
validação nativa no Windows nem execução do CI do GitHub nesta etapa.

As verificações locais também passaram: seis testes pytest, Ruff, Bandit e
`makemigrations --check --dry-run`. O mypy foi executado em dois arquivos de
domínio, sem erros; isso não representa uma análise de tipos de todo o projeto.
O Bandit registrou um aviso anterior sobre uma anotação `nosec` em `backup.py`.
O `pip-audit` não identificou vulnerabilidades conhecidas em `requirements.txt`
no momento da execução; esse resultado pode mudar com novas divulgações.

Ainda faltam homologação com arquivos reais de cada
versão de fornecedor, política de retenção e um fluxo de reconciliação de ativos
e achados após a revisão. A fase não liga honeypot público, não varre a rede e
não chama APIs pagas.
