# Reanálise técnica — 10/11/2026

## Escopo e método

O pedido abrange todos os arquivos, decisões e funcionalidades. Foram inventariados
os arquivos versionados e revisados caminhos de autenticação, configurações, camadas,
modelo de risco, dependências, integrações, implantação e parte da documentação.
Não foi realizada leitura manual linha a linha das aproximadamente 24 mil linhas
Python nem análise independente de cada decisão histórica. O [índice automático de
arquivos](INVENTARIO_ARQUIVOS_2026-11-10.md) ajuda a localizar o conteúdo. Testes exercitam
os casos neles definidos; não garantem correção universal, segurança ou otimalidade.

Explicação acessível das funções, linguagens, bibliotecas e serviços:
[guia simples](GUIA_SIMPLES_REANALISE_2026-11-10.md).

## Achados e correções

### Alta: Django fixado em versão anterior a atualizações de segurança

`requirements.in` e `requirements.txt` fixavam Django 5.2.17. As notas oficiais de
[5.2.18](https://docs.djangoproject.com/en/5.2/releases/5.2.18/) e
[5.2.19](https://docs.djangoproject.com/en/5.2/releases/5.2.19/) documentam várias
correções, inclusive parsing HTTP, multipart e tratamento de `Vary`. A existência
do aviso em uma dependência não prova que cada CVE seja explorável neste projeto;
o risco depende dos caminhos usados e da implantação.

**Alteração:** atualizar o requisito para 5.2.19, mantendo a mesma série LTS. O wheel
foi instalado em pasta isolada para testes sem sobrescrever o ambiente anterior.
O servidor real só recebe a correção após instalar requisitos, reconstruir imagens
e reiniciar; os resultados locais não atualizam uma implantação existente.

### Média: Gunicorn antigo e fora da lista de suporte

O projeto fixa Gunicorn 23.0.0. A [política oficial do Gunicorn](https://github.com/benoitc/gunicorn/security/policy)
marca essa versão como não suportada. Isso é risco de manutenção; não se conclui
apenas daí que haja uma CVE explorável no caminho WSGI do Sauron. Não foi trocada
nesta revisão: a migração entre versões principais precisa de ensaio em Linux com
proxy real e Docker, que não estavam disponíveis para validação aqui. Tratar como
prioridade antes de exposição pública e reavaliar os avisos da versão escolhida.

### Média: explicação técnica divergia do código

`EXPLICACAO_SAURON.md` atribuía a solução linear a `numpy.linalg.solve`, sugeria uso
de `eval` restrito e citava um método de equipamento não encontrado. Foram ajustados
os trechos para refletir `scipy.sparse.linalg.splu`, a interpretação da árvore
sintática sem `eval`, o cálculo condicional do número de condição e os métodos reais.
Outros documentos históricos não foram todos comparados linha a linha.

### Atenção: escopo, manutenção e otimização

Há muita funcionalidade e documentação para um protótipo. Linguagens e bibliotecas
são justificáveis, mas tamanho e variedade ampliam a superfície de teste e a
dificuldade de demonstração. Não há prova de que toda função seja necessária, de
que nenhuma abstração possa ser simplificada ou de que a solução seja ótima.
Qualquer otimização deve começar por um cenário, métricas e perfilamento, seguida
de teste de comportamento. O teste sintético de 5.000 ativos não representa carga
real, concorrência, desempenho de interface ou servidor em produção.

## Evidências executadas

- Suíte Django da versão anterior: 388 testes passaram em banco descartável.
- Suíte Django com Django 5.2.19 carregado da pasta isolada: 388 testes passaram.
- Testes pytest: 6 passaram; JavaScript: 12 cenários passaram.
- Teste SMTP local: conexão loopback com STARTTLS, certificado temporário e
  autenticação simulada passou. Não houve envio para provedor ou destinatário real.
- Ruff e Bandit passaram; há supressões preexistentes de Bandit para subprocesso
  de restauração e conexão HTTP. A checagem Django de produção com segredos
  efêmeros passou. Essas ferramentas não substituem revisão ou pentest.
- `makemigrations --check --dry-run` não encontrou alterações de esquema; `pip check`
  não identificou conflitos no ambiente de teste. Isso não cobre os pacotes do sistema.
- A auditoria `pip-audit` não terminou nas duas tentativas desta execução; não há
  resultado completo para dependências transitivas nem imagem de sistema.
- A consulta direta à API do PyPI retornou listas de vulnerabilidades vazias para
  as oito versões diretas fixadas após a mudança. Isso reflete somente dados
  publicados na API consultada e não substitui a auditoria de transitivas ou imagem.
- Carga local com Django 5.2.19 e dados descartáveis: 100 fluxos de senha + TOTP
  passaram com até 10 logins simultâneos; no acesso administrativo, 4 receberam 200
  e 96 receberam 403, conforme esperado. Uma rajada de 100 tentativas de senha no
  mesmo IP teve 95 respostas 302 e 5 respostas 429 pelo limitador. O teste usou
  SQLite e WSGI com threads em loopback, não o container de produção. Evidência:
  [carga-local.json](evidencias/reanalise_20261110/carga-local.json).
- A etapa de 100 fluxos graduais de login registrou 8.087 operações SQL no conjunto
  dos pedidos, um ponto para perfilamento posterior. Não é possível concluir desse
  número isolado quais consultas são dispensáveis ou aplicar uma otimização segura
  sem separar autenticação, auditoria, MFA e dados de sessão.

Os testes de MFA verificam sessões, TOTP, repetição de código, expiração, limite de
tentativas, SMTP simulado, e separação de permissões entre leitores e administradores.
Eles não demonstram envio efetivo por Gmail/UFU, todas as contas de uma instalação,
nem equivalem à validação do fluxo real após a implantação.

## Pendências prioritárias

1. Executar `pip-audit` com rede disponível incluindo dependências transitivas;
   verificar também bibliotecas de desenvolvimento, imagem e sistema operacional.
2. Atualizar e testar Gunicorn suportado em Linux, com Docker e proxy reais.
3. Construir a imagem corrigida, testar login/sessão/CSRF através de HTTPS e SMTP
   real, incluindo caixas controladas Gmail e UFU, e repetir após reinício.
4. Verificar restauração de backup e âncora independente; confirmar operação por
   24 horas no servidor exigido pelo trabalho, sem produzir evidências fictícias.
5. Mapear rotas e funções sem testes de comportamento e fazer avaliação de carga
   com dados e metas acordadas, antes de reduzir ou acelerar módulos específicos.
