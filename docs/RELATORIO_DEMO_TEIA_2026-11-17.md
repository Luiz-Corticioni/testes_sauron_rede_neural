# Empresa fictícia, teia de dependências e painel

## Empresa fictícia

Na visão geral, o superusuário pode escolher **Preparar uma demonstração fictícia → Carregar empresa fictícia**. A operação exige sessão autenticada, MFA e POST com CSRF. Também pode ser feita por `python manage.py seed_demo --empresa`. Use uma base de demonstração separada: a carga recusa um inventário que já possua salas, ativos, vulnerabilidades, incidências ou dependências. A operação é transacional e a repetição não modifica os registros existentes. A opção antiga `seed_demo` permanece disponível.

A empresa Aurora contém 31 ativos em nove tipos, nove vulnerabilidades e mais de 50 dependências ponderadas. Os dados adicionais são identificados como fictícios; a visão geral exibe aviso destacado. Os pesos e notas são hipóteses didáticas, não observações. Não há associação inventada a CVEs reais nem EPSS simulado. Os indicadores existentes continuam a refletir os dados e as hipóteses cadastrados; não demonstram a situação de uma organização real.

## Mapa e visual

O mapa distribui os nós em anéis com os ativos que possuem mais vínculos próximos ao centro. A posição é puramente visual; as setas continuam do fornecedor para o dependente. Foco e ponteiro destacam alcance na janela exibida, e a tabela e a consulta completa de dependentes permanecem disponíveis. Um caminho indica uma dependência cadastrada, não exploração, contágio comprovado ou probabilidade de ataque. A visualização mantém o limite de 60 nós.

Foram adicionados contraste, hierarquia visual e cores em brasa ao painel e ao mapa sem fontes, bibliotecas ou serviços externos. O aviso da demonstração e o formulário seguem as permissões existentes. Não houve alteração no cálculo de risco.

## Verificações

Os testes cobrem diversidade e quantidade de ativos, cálculo do risco, vínculos exibidos, repetição, recusa a usuário comum, exigência de MFA e método POST. O teste JavaScript verifica direção da seta, nome acessível e alcance por foco e passou a rodar no CI. A suíte completa e o resultado do CI devem ser consultados na execução do commit correspondente; não são evidência de desempenho ou de segurança de uma instalação em produção.
