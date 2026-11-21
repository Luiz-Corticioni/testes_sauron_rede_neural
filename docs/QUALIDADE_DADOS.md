# Qualidade das evidências

O indicador `sauron.qualidade/1` mede **completude de critérios declarados**;
não mede segurança, probabilidade de ataque, precisão do inventário ou qualidade
estatística das previsões. É uma convenção local de apoio à revisão, não um
indicador calibrado nem certificação de qualidade.

Cada componente informa origem, data, idade quando disponível, quantidade que
atende ao critério e denominador. O índice é a média aritmética dos percentuais
dos componentes com pesos iguais. Se qualquer componente não tiver denominador
ou contexto determinável, o índice composto é **indisponível**. Zero em um
componente significa que nenhum dos registros conhecidos satisfaz aquele
critério; não significa risco zero nem prova ausência de vulnerabilidades.

## Ativo e serviço de negócio

São considerados três componentes:

1. **EPSS:** fração das incidências elegíveis com EPSS coerente com sua
   observação de origem e datado dos últimos dois dias. A data exibida é a mais
   antiga entre as observações recentes consideradas. Sem incidências elegíveis,
   a fração é indeterminada: o inventário pode estar incompleto.
2. **Revisão de relações:** para ativo, use perímetro e camada explícitos; vale
   um se a revisão do contexto atual estiver no prazo e sem lacunas, zero se
   houver revisão ausente, vencida, com lacunas ou contexto alterado. Para serviço,
   é a fração dos ativos operacionais do perímetro com revisão válida na camada
   de negócio. A declaração não comprova descoberta completa da rede.
3. **Fontes NVD e KEV:** fração das duas fontes com dados locais atuais e sem
   falha na última tentativa registrada. É uma condição **global do inventário**,
   não uma confirmação de aplicabilidade ao ativo. Se a amostra de NVD for
   incompleta, o componente é indeterminado. O painel de fontes mostra datas,
   lacunas e limites da amostra; não testa conectividade ao abrir a página.

A ficha de ativo permite escolher um perímetro e a camada de rede ou negócio;
sem escolha, a revisão é indeterminada. A camada de identidade e seu principal
podem ser informados na API. A ficha de serviço usa seu perímetro declarado. As
consultas exigem as permissões de inventário, vulnerabilidades e cobertura; a
falta de permissão não vira zero e os componentes não são exibidos à conta.

As rotas com sessão e MFA são `GET /api/v1/qualidade/ativos/<id>/` e
`GET /api/v1/qualidade/servicos/<id>/`. Para um ativo, os parâmetros opcionais
`perimetro`, `tipo` e `principal` definem o contexto de revisão. O contrato está
em [OpenAPI](openapi-v1.json). Credenciais de integração existentes não recebem
acesso implícito a essas rotas. `GET /api/v1/qualidade/fontes/` apresenta a
situação das fontes; dados de importações e iscas exigem permissões adicionais.
O histórico de scanner registra tentativas de gravação, não as prévias; erros
conservam apenas uma categoria genérica, sem armazenar o conteúdo do arquivo.

## Simulação de 30 dias

O resultado Monte Carlo inclui a fração de EPSS recentes e coerentes, preservando
o contrato `sauron.montecarlo/30d-v1`. A validação independente das premissas
financeiras e a cobertura de relações do cenário são indeterminadas porque o
fluxo atual não registra essas evidências nem identifica seu perímetro/camada.
Por isso, o índice composto financeiro fica indisponível, inclusive quando todas
as entradas EPSS estão recentes. As premissas continuam sendo hipóteses; EPSS
não é probabilidade de comprometimento ou perda financeira do cliente.

Nos cenários FAIR e de interrupção, a presença de campos de origem é contada
como **declaração**, não como confirmação de que as fontes sejam corretas. O
índice composto também permanece indisponível pela ausência de validação
independente. Em interrupção com perdas secundárias, a origem pode ser informada
na tela, mas não é recebida pelo serviço de cálculo e, por isso, esse componente
é indicado como indeterminado. Execuções FAIR históricas que não registraram
esse indicador não recebem uma avaliação retroativa.

Este indicador inicial não avalia todas as telas e todos os tipos de fonte ou
cenário. Em particular, a classificação de procedência e validação das premissas
financeiras precisa de evidência explícita antes de compor um número.
