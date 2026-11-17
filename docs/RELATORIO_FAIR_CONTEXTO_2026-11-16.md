# Relatório: contexto da ameaça e cobertura FAIR

Foram adicionados campos opcionais para registrar valor, esforço e risco percebidos pela ameaça, assim como suas habilidades e recursos. Eles ajudam a justificar as faixas escolhidas sem atribuir pesos arbitrários ou produzir probabilidades aparentemente objetivas a partir de descrições textuais. O contexto é incluído nas cópias e nos registros de execução.

A matriz de cobertura relaciona os conceitos centrais do FAIR à implementação e declara explicitamente as limitações. A migração acrescenta campos vazios aos cenários existentes. O backup antes da migração omite essas colunas quando ainda não existem, preservando o caminho de atualização.

Os testes verificam criação, exibição e cópia do contexto e o backup no esquema anterior à migração. Os demais relatórios FAIR detalham o motor, as permissões, a comparação e o histórico de simulações.
