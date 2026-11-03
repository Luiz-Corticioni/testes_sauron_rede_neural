# Homologação do grafo por camada

Use apenas banco e ativos de teste. Não copie estas relações para representar sua rede real. A evidência de todos os registros abaixo deve dizer **“Cenário sintético de homologação; sem verificação de ambiente real”**.

1. Cadastre três ativos operacionais A, B e C. Anote seus códigos reais.
2. Em Relações por camada, cadastre a tabela abaixo. Use escopo exato `homologacao`, fonte `roteiro sintético`, data observada de hoje, revisão daqui a 30 dias e vigência marcada.

| Origem | Destino | Camada | Protocolo | Porta destino | Principal | Privilégio |
|---|---|---|---|---|---|---|
| A | B | REDE | tcp | 443 | vazio | vazio |
| B | C | REDE | tcp | 5432 | vazio | vazio |
| C | B | NEGOCIO | vazio | 0 | vazio | vazio |
| B | A | NEGOCIO | vazio | 0 | vazio | vazio |
| A | B | IDENTIDADE | vazio | 0 | laboratorio/svc | LEITURA |

3. Na análise REDE, escolha origem A, destino C e escopo `homologacao`. Resultado esperado: alcance 2, menor caminho até C com 2 saltos, sem grupos cíclicos.
4. Simule retirar a relação B→C. Resultado esperado: alcance 1, C deixa de ser alcançável. O cadastro continua vigente.
5. Cadastre uma segunda relação REDE A→B na porta 8443. Simule retirar apenas a primeira A→B, da porta 443: B e C continuam alcançáveis pela alternativa.
6. Analise NEGOCIO com origem C. O caminho é C→B→A. A camada não deve reutilizar a direção ou as portas da rede.
7. Analise IDENTIDADE com origem A e principal `laboratorio/svc`. Apenas B aparece. O caminho de rede B→C não é acrescentado à análise de identidade.
8. Abra uma evidência pelo link do caminho. Confira origem/destino, fonte, datas e autoria. Revogue explicitamente um vínculo e confirme que ele sai da próxima análise da sua camada, permanecendo na lista.

Os resultados comprovam o funcionamento do cenário cadastrado. Não comprovam instalação, tráfego real, autenticação ou exploração.
