# Sauron: como funciona e por que foi construído assim

Esta explicação foi preparada em 10/11/2026 a partir do código, das configurações,
dos testes e dos relatórios disponíveis. Quando digo que uma decisão «facilita» algo,
explico o benefício técnico observado; não afirmo conhecer a intenção histórica de
cada autor. O projeto é grande: o Git listava 481 arquivos, incluindo 286 arquivos
Python e dados/documentação. Esta revisão não examinou manualmente cada linha nem
prova que todas as funcionalidades ou integrações funcionem em todo ambiente.

## O que o Sauron faz

O sistema mantém uma lista de equipamentos, programas, vulnerabilidades e vínculos.
Um operador pode registrar que uma falha afeta um equipamento e que um equipamento
depende de outro. A partir disso, o Sauron produz relatórios e ajuda a priorizar o
tratamento. Seus cálculos são modelos de apoio à decisão, não um scanner que prova
que houve invasão ou que todos os computadores estão seguros.

Pense em quatro partes: a **interface** recebe o pedido; a **aplicação** organiza a
operação; o **domínio e a matemática** representam as regras; o **banco e serviços
externos** guardam ou fornecem dados. Web, terminal e tarefas agendadas reaproveitam
parte dos serviços, mas existem acoplamentos diretos ao ORM Django: a separação não
é completa. Leia [ARQUITETURA.md](ARQUITETURA.md) para localizar os módulos.

## Funcionalidades, razões e limites

| Função | Como funciona e por que existe | Limitação ou cuidado |
|---|---|---|
| Cadastro de ativos | Classes como Servidor e Notebook guardam dados e comportamentos próprios; o ORM os persiste. Tipos ajudam a organizar a consulta e demonstram herança. | Cadastro é uma declaração: não comprova existência nem estado real. O identificador inclui informações de tipo e fabricante, o que dificulta mudanças futuras. |
| Salas e software | Associam localização e componentes aos ativos, permitindo consultas e contexto para decisões. | A informação precisa ser mantida atualizada; não equivale a descoberta automática da rede. |
| Vulnerabilidades e incidências | A vulnerabilidade é registrada uma vez; a incidência liga a falha ao ativo e guarda situação/evidência. Evita repetir o mesmo registro em todos os ativos. | Uma CVE cadastrada não prova que o ativo esteja afetado. Analistas devem verificar produto e versão. |
| Dependências e mapa | Um ativo pode depender de outro; os vínculos formam um grafo para mostrar alcance e propagação matemática. | Caminho no grafo é uma relação declarada, não prova de exploração ou de trânsito de rede. |
| CVE, NVD e KEV | NVD fornece dados públicos das CVEs; CISA KEV indica falhas reconhecidas como exploradas. Cache e limites reduzem consultas repetidas. | Rede, disponibilidade e atualização das fontes importam. KEV não prova comprometimento do seu ambiente. |
| CVSS | Registra nota, versão e vetor; o código calcula e compara aspectos de CVSS 3.1. | CVSS mede severidade segundo critérios padronizados; isoladamente não mede risco específico da organização. |
| EPSS | Consulta a FIRST e guarda observações com data, permitindo conferir se a estimativa está recente. | A probabilidade é uma estimativa para exploração no ecossistema, não a chance de um ativo específico ser invadido. |
| SSVC | Registra fatores e uma decisão de priorização por incidência, com justificativas e contexto. | O resultado depende das respostas humanas e das evidências disponíveis; não corrige a falha. |
| SBOM, PURL e VEX | Identificam componentes declarados e informações sobre aplicabilidade de vulnerabilidades. | Documentos e declarações podem estar incompletos; exigem revisão e proveniência. |
| Risco puro | Faz `b = Mv` e resolve `(I-A)x = b`, somando CVSS próprias e influência das dependências. O solver esparso evita preencher com zeros uma matriz grande. | A direção e os pesos são hipóteses do inventário. O resultado é um índice, não uma probabilidade; ciclos ou pesos inválidos podem inviabilizar o modelo. |
| Perfil operacional | Acrescenta fatores e informações ao cálculo para uma análise interna alternativa. | Não confundir com o perfil puro exigido no trabalho; fatores precisam de justificativa. |
| Modo Euler | Interpreta expressões matemáticas restritas e oferece métodos como derivação, integração e resolução aproximada de equações. | Método numérico e passo influenciam o resultado. O interpretador usa uma lista de operações permitidas em vez de executar Python arbitrário. |
| Monte Carlo | Gera muitos cenários de perda com hipóteses de custo e exposição, em janela de 30 dias. Limites de tamanho e concorrência procuram controlar consumo. | Sem calibração e dados de custos, a saída é um cenário ilustrativo, não promessa de perda futura. |
| Sistema imune | Sugere associações a partir de padrões e evidências anteriores para apoiar triagem. | É heurístico; pode errar. Sugestões não substituem revisão nem devem ser tratadas como detecção comprovada. |
| Relações e cobertura | Registra relações por camada e revisões de cobertura para mostrar o que foi observado, quando e com qual evidência. | Cobertura depende do perímetro declarado e de revisões dentro do prazo; não é certeza sobre toda a infraestrutura. |
| Alertas e rotinas | Agendador executa verificações e registra sinais operacionais para acompanhamento. | Precisa estar rodando; reconhecer um alerta não corrige sua causa. |
| Relatórios, CSV e JSON | Facilitam consulta e intercâmbio; exportação CSV trata valores que podem ser interpretados como fórmulas. | Os arquivos podem conter dados sensíveis. JSON é exportação explícita; o banco principal do site é SQL. |
| Auditoria | Registra ações e usa encadeamento e HMAC para ajudar a perceber alterações indevidas. | Sem proteger a chave e manter âncoras independentes, um administrador da infraestrutura pode comprometer a evidência. |
| Backup | Oferece backup lógico cifrado e restauração em banco novo. | Só existe confiança após testar restauração e guardar chave e cópia em locais separados. |
| Docker | Empacota a aplicação e mantém volume para dados; preparação, web e agendador são serviços distintos. Há proxy HTTPS opcional. | Build, rede, TLS, reinício e 24 horas ainda precisam de execução real no ambiente de destino. |

## Login, permissões e segundo fator

1. A senha passa pelo mecanismo de autenticação do Django. Há limitação de
   tentativas e registros de auditoria para dificultar tentativas repetidas.
2. Depois da senha, a sessão precisa de um segundo fator: aplicativo autenticador
   TOTP ou código enviado ao e-mail cadastrado, quando SMTP está configurado.
3. O código por e-mail é temporário e de uso único; são limitados reenvios e
   tentativas. O servidor guarda uma verificação criptográfica, não o código puro.
4. Cada operação protegida exige permissões; testes verificam que usuário comum
   não acesse administração nem altere recursos que não lhe cabem. A criação do
   primeiro administrador é um comando local e não cria sessão autenticada.

Os testes usam banco descartável, mensagens em memória e códigos TOTP reais gerados
para contas fictícias. Isso verifica o comportamento do código nos cenários cobertos;
não confirma entrega em Gmail/UFU, configuração DNS/TLS, servidor SMTP, navegador
ou a segurança da caixa postal de um usuário real. A alternativa por e-mail depende
da proteção dessa caixa. Consulte [EMAIL_E_MFA.md](EMAIL_E_MFA.md).

## Linguagens e formatos

| Linguagem/formato | Onde aparece | Motivo prático |
|---|---|---|
| Python | Regras, serviços, testes, CLI, cálculos e Django | Permite compartilhar regras entre web e terminal e dispõe de bibliotecas numéricas e de segurança. |
| HTML e templates Django | Páginas do site | Descrevem a estrutura das páginas; os templates inserem dados enviados pelo servidor. |
| CSS | Estilo e apresentação | Separa cores, espaçamento e aparência da estrutura e das regras. |
| JavaScript | Interações e chamadas de telas | Permite atualizar partes da interface sem reconstruir toda a aplicação. |
| SQL | Consultas, migrações e armazenamento SQLite via ORM | Relaciona ativos, vulnerabilidades e ocorrências; transações e restrições ajudam a preservar integridade. |
| JSON | APIs, configurações, exportações e dados de teste | Formato de troca legível e suportado por Python e navegadores. |
| YAML, Dockerfile e shell/PowerShell/batch | Compose, CI e instalação | Descrevem serviços e automatizam tarefas em Linux e Windows. |

## Bibliotecas de execução

As versões exatas ficam em `requirements.txt`; ferramentas para desenvolvedores ficam
em `requirements-dev.txt` e não precisam ser instaladas para operar o produto.

| Biblioteca | Uso observado |
|---|---|
| Django | Servidor web, autenticação básica, formulários, sessões, ORM e migrações. |
| django-otp | Dispositivos e validação de códigos de aplicativo autenticador (TOTP). |
| Gunicorn | Processo WSGI para servir Django em implantação Linux/container. |
| WhiteNoise | Entrega de arquivos estáticos produzidos no build. |
| NumPy | Vetores e operações numéricas utilizadas nos modelos e simulações. |
| SciPy | Matrizes esparsas, resolução de sistemas e rotinas numéricas. |
| cryptography | Recursos criptográficos, incluindo Fernet para backups cifrados. |
| packageurl-python | Leitura/normalização de identificadores PURL de componentes. |

Também são usados recursos da biblioteca padrão do Python, como `sqlite3`, `json`,
`hashlib`, `hmac`, `secrets`, `smtplib` e `urllib`. Ferramentas de desenvolvimento
incluem pytest, Ruff, Bandit, pip-audit, pip-tools e gerador de SBOM CycloneDX.
Elas ajudam a verificar o projeto, mas não certificam a segurança de cada versão.

## APIs e serviços externos

- **NVD/NIST:** consultas de CVEs; uma chave NVD é opcional. Sem rede ou com limite
  atingido, uma consulta pode falhar e o resultado deve ser apresentado como tal.
- **CISA KEV:** catálogo de vulnerabilidades conhecidas como exploradas.
- **FIRST EPSS:** estimativas e percentis por CVE, com data e histórico local.
- **SMTP configurado pelo responsável:** transporte de mensagens MFA. Gmail e UFU
  podem ser destinatários; não é possível enviar sem serviço de saída autorizado.
- **API HTTP do próprio Sauron:** usada pela interface e por integrações autorizadas;
  as rotas de dados exigem autenticação/permissões conforme o caso.

Não foi encontrada integração OpenAI no código pesquisado; esta revisão não adiciona
chaves ou chamadas à OpenAI. Ausência de texto encontrado não é garantia sobre
configurações externas ou sobre todo software instalado na máquina.

## Julgamento técnico e próximos passos

1. A versão Django fixada em 5.2.17 estava atrás de correções de segurança oficiais.
   A atualização desta revisão permanece na série 5.2 e exige instalação/rebuild e
   testes na máquina de destino. Veja [notas 5.2.18](https://docs.djangoproject.com/en/5.2/releases/5.2.18/)
   e [notas 5.2.19](https://docs.djangoproject.com/en/5.2/releases/5.2.19/).
2. A complexidade do produto é alta para um protótipo. Manter inventário, controle
   de acesso, vulnerabilidades e risco exigido como núcleo e tratar funções
   experimentais como opcionais reduz esforço de explicação e manutenção.
3. Existem testes significativos, mas muitas rotas, combinações de permissões,
   navegadores e integrações reais não têm prova completa. A cobertura pytest de
   uma seleção de módulos não é cobertura integral do sistema.
4. O repositório tem documentação histórica que pode divergir da implementação.
   Corrigimos nesta revisão descrições incorretas sobre o solver e sobre `eval`;
   outros documentos históricos não foram todos verificados linha por linha.
5. Não existe uma maneira de garantir que todo código é «o mais otimizado possível»
   sem definir carga e objetivos, medir gargalos e comparar alternativas. Mudanças
   em desempenho devem vir de medições reproduzíveis e de testes de regressão.
6. Antes de hospedar: validar Docker, HTTPS, SMTP com caixa real, backups, restrições
   de rede e prova de 24 horas. Não colocar segredos em relatórios ou repositórios.

Os resultados concretos desta execução ficam no [relatório técnico](RELATORIO_REANALISE_2026-11-10.md).
