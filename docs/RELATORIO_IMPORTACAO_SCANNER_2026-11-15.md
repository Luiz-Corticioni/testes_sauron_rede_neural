# Importação offline de relatório Trivy

Foi adicionado importador do formato JSON SchemaVersion 2 do Trivy, limitado a 2 MB e 5.000 achados. A prévia exibe CVE, pacote e versão; itens sem esses campos são contados como ignorados. O operador informa ativo, origem e escopo e reenvia o arquivo após revisar. Uma assinatura temporária vincula a confirmação ao usuário, ao contexto e aos dados minimizados.

Os dados preservados são evidência declarada pendente de análise: não se executa scanner, não se acessa a rede, não se cria incidência automaticamente, e o relatório não substitui um SBOM completo. Data da observação e data de recebimento são guardadas separadamente. Descrições, caminhos e metadados adicionais do arquivo não são arquivados. Os resultados atuais podem ser conferidos e registrados manualmente no inventário; não foi implementada uma decisão individual com histórico de aprovação para cada achado.

Passaram 31 testes de scanner e documentos; a prévia também foi exercitada contra um relatório Trivy real previamente gerado da imagem local (47 pares reconhecidos, nenhum ignorado). Um comando inicial de testes usou um nome de módulo inexistente; foi corrigido e a execução completa passou. Ruff passou nos arquivos novos. O importador não autentica a origem dos dados nem prova que o pacote pertence ao ativo escolhido.
