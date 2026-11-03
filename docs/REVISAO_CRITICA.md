# Revisão crítica da aplicação — 27/10/2026

Escopo: inventário, salas, software, vulnerabilidades/CVE, incidências e aprovações,
risco/Monte Carlo, sistema imune, auditoria, backup/restauração, operação e instalação.
Base inicial: 97 testes passam. Isso não comprova ausência de falhas; a revisão
acrescenta cenários adversariais, operações POST e verificações de implantação.

O documento adicional de requisitos mínimos ainda não foi recebido. A aderência
a esse documento permanece sem avaliação; não se inventam critérios acadêmicos.

ID | achado | severidade | situação | evidência
---|---|---|---|---
RC01 | Renovação pode reutilizar aprovação; edição inócua reabre decisão; operador altera software | alta | corrigido | tests.test_revisao_decisoes (5 casos vermelho→verde)
RC02 | Confirmação crítica por operador sem MFA; confiança TLS de proxy não vinculada a CIDR | alta | corrigido | tests.test_revisao_seguranca (MFA e protocolo de proxy)
RC03 | Restauração publica banco antes de terminar; corrida de sobrescrita e falha parcial | alta | corrigido | tests.test_revisao_backup e tests.test_backup
RC04 | Âncora ausente/vazia considerada válida; versão de cadeia adulterada causa exceção | alta | corrigido | tests.test_revisao_auditoria e tests.test_auditoria_adversarial
RC05 | POST vazio fica sem erros; falha concorrente no cadastro de software vira erro 500 | média | corrigido | tests.test_revisao_funcional
RC06 | Exportação chamada inventário omite software, evidências e demais cadastros | média | corrigido | tests.test_revisao_exportacao
RC07 | Memória arquivada não conta reaprendizado; limite trunca componentes; VEX alheio suprime hipótese | média | corrigido | tests.test_revisao_imune
RC08 | Ausência de bootstrap Linux com instalação e atualização protegida | média | implementado; Linux real pendente | tests.test_instalacao_linux e scripts/test_instalador_linux.sh
RC09 | API/cache densificam matrizes apesar do núcleo esparso | alta | corrigido | tests.test_revisao_esparsa, 5.000 ativos com JSON e apresentação
RC10 | Indicador acusa indisponibilidade em login/MFA por consultar saúde protegida | média | corrigido | reprodução e confirmação visual no navegador; HTTP público 200

## Parecer crítico

A aplicação reúne inventário, decisões de segurança e experimentos matemáticos úteis,
mas isso não a torna uma plataforma de detecção nem comprova prontidão operacional.
A suíte inicial de 97 testes passava mesmo com os problemas RC01–RC10. Ela era
insuficiente para alguns caminhos de aprovação, falhas de recuperação e apresentação
sob volume. Os cenários novos cobrem esses caminhos; não provam ausência de defeitos.

O núcleo de risco calcula uma propagação linear sob pesos e hipóteses informados.
O índice de 0–100 não é probabilidade de ataque. As hipóteses do sistema imune
continuam sujeitas a revisão humana; similaridade não comprova vulnerabilidade.
Monte Carlo depende dos custos/distribuições inseridos; os valores padrão não são
uma previsão financeira calibrada. CPE, faixas e VEX exigem contexto e qualidade da fonte.

Os módulos experimentais de Noisy-OR, contágio e EDO permanecem testes/laboratório;
não são apresentados como integrações operacionais prontas. Inventário de software
mínimo também não equivale a uma SBOM completa. A configuração continua priorizando
SQLite; implantação PostgreSQL e migração de dados exigem procedimento próprio.

## Validação por área

Área | evidência automatizada | verificação adicional
---|---|---
Ativos, salas, software e vínculos | test_formularios_seguros, test_remediacao_dominio, test_regressao, test_revisao_funcional | telas e tabelas no navegador
Incidências, aceites e correções | test_remediacao_operacao, test_revisao_decisoes | fila paginada aprovar/devolver; termos do servidor
Login, papéis e MFA | test_mfa, test_remediacao_seguranca, test_revisao_seguranca | login com senha + TOTP real de conta descartável
CVE/KEV e matching | test_remediacao_nvd, test_matching, test_revisao_imune | tela CVE/KEV; testes usam fixtures e bloqueiam rede
Imunidade e tolerâncias | test_remediacao_imune, test_ciclo_snapshot, test_revisao_imune | painel e curva de memória
Risco, diagnóstico e gráficos | test_regressao (golden), test_nao_regressao, test_risco_esparso, test_revisao_esparsa | mapa, matrizes, prioridades; cenário INC-0001 reduziu 9,8→0 sem gravação
CVSS e Euler | test_nao_regressao, test_cvss_ambiental, test_edo | vetores CVSS e payloads hostis; tela Euler
Monte Carlo e modelos experimentais | test_montecarlo, test_integracao_montecarlo, test_noisy_or, test_contagio, test_caminhos_ataque | tela e resposta da simulação padrão; sem calibração de campo
CSV e exportações | test_regressao, test_revisao_funcional, test_revisao_exportacao | importador, permissões e auditoria de sucesso
Auditoria e recuperação | test_auditoria_adversarial, test_revisao_auditoria, test_backup, test_revisao_backup | verificação em banco descartável e falhas/race de publicação
Operação e Linux | test_preparacao_banco, test_saude, test_heartbeat, test_instalacao_linux | bootstrap de aplicação novo/repetido, estáticos em produção e rotinas offline

No navegador: dashboard e 16 áreas de navegação percorridas; nenhum erro de console
na verificação. A cobertura de telas não equivale a testar toda combinação de campos
ou todos os fluxos administrativos. Certificados e incidentes continuam administrados
pelo Django Admin; seus alertas e persistência são exercitados na suíte existente.

## Contratos alterados

`exportar_inventario --saida arquivo.json` agora gera `sauron.inventario/v2`, com
coleções dos cadastros/evidências. Exclui modelos de contas, dispositivos MFA, sessões e cadeia
de auditoria. Campos livres do inventário podem conter informações sensíveis. É informação sensível de inventário, sem criptografia; use backup cifrado
para recuperação. `--legado` preserva as quatro coleções históricas.

As APIs de risco e simulação mantêm matrizes em arrays quando ambas as dimensões são
até 300. Acima disso, retornam objeto CSR com `formato`, `shape`, `data`, `indices`,
`indptr`. Consumidores externos devem aceitar essa representação. O frontend, CLI e
diagnóstico do projeto foram adaptados. O teste de 5.000 ativos também serializa o JSON,
limita-o a menos de 3 MB e exercita diagnóstico, grafo de 60 nós e mapa de 40×40.
Essas janelas limitam a exibição; o cálculo considera o inventário completo.

Fora de DEBUG, `verificar_auditoria` exige âncora por padrão. Arquivo vazio ou malformado
falha. Em desenvolvimento, ausência é explicitamente informada. `--somente-cadeia`
serve à recuperação isolada: não atesta que âncoras externas foram recuperadas.
Uma âncora local não protege contra quem controla simultaneamente banco, arquivo e
chave HMAC; o coletor externo, controle de acesso e custódia continuam necessários.

## Limites de validação

Nenhuma alteração deve tocar o .env ou o banco de uso do usuário.
Testes e navegação usarão configuração e dados descartáveis. O host desta revisão
é Windows; WSL não está instalado. Execução real em Fedora/RHEL será distinguida de
testes do instalador com comandos simulados e de jobs configurados para CI.


RC01: fila paginada com aprovar/devolver, termos persistidos no servidor e motivo auditado. Uma mudança material exige nova decisão; observação administrativa não apaga aprovação.


## Pendências verificáveis

- Documento adicional de requisitos mínimos ainda não recebido. O texto de remediação
  anexado foi considerado; não substituí o documento adicional por critérios inventados.
- Instalador: sintaxe Bash e orquestração simulada verificadas; preparação real da
  aplicação em cópia Windows isolada. Containers Fedora/Rocky configurados na CI,
  ainda sem resultado de execução neste trabalho. Não se certifica instalação Linux real.
- Sem ensaio contínuo de 24 horas, proxy TLS real, SELinux/firewall ou recuperação em
  host externo nesta revisão. São validações de implantação ainda necessárias.
- A auditoria de dependências consultou o PyPI nesta revisão e não encontrou
  vulnerabilidades conhecidas. Isso vale para o conjunto resolvido nessa consulta;
  os pins ainda não possuem hashes de supply chain e devem ser reavaliados na CI.

A instalação Linux está documentada em [INSTALACAO_LINUX.md](INSTALACAO_LINUX.md).


## Resultado desta execução

- **123 testes Django/unittest aprovados** (34,7 s na execução final).
- `check`, `makemigrations --check --dry-run`, Ruff, Bandit e `check --deploy`
  com ambiente de produção simulado aprovados.
- `pip-audit -r requirements.txt`: nenhuma vulnerabilidade conhecida encontrada.
- Sintaxe e testes shell simulados aprovados no Bash do Git; não confundidos com
  execução em Fedora/RHEL.
- Preparação nova, repetida, diagnóstico, estáticos em modo produção e rotinas
  offline aprovados em cópia descartável. Navegador: senha/TOTP, 16 áreas,
  simulação sem gravação e indicador público de saúde verificados.

O benchmark do núcleo com 5.000 ativos/4.999 arestas foi cerca de 10 ms neste host;
é um cenário sintético, não um SLA. O novo teste inclui serialização e consumidores
visuais, mas não atesta latência sob múltiplos usuários ou carga de produção.


## Rastreabilidade Git

Branch: `revisao/linux-funcional`, a partir de `2deab08`.

ID | commit | alteração
---|---|---
RC01 | `7705a4a` | decisões segregadas e fila de revisão
RC02 | `dd51d39` | reforçar MFA e confiança no protocolo do proxy
RC03 | `36e149a` | publicar restauração apenas após validação
RC04 | `335f94c` | exigir âncoras em produção e rejeitar adulterações
RC05 | `3fc20d2` | tratar entradas vazias e conflitos no cadastro web
RC06 | `4f34f48` | exportar cadastros completos com controle de auditoria
RC07 | `e04692b` | corrigir cobertura de componentes e reaprendizagem
RC08 | `b60e240` | automatizar instalação Fedora e RHEL com atualização protegida
RC09 | `7266844` | preservar matrizes esparsas na API e apresentação
RC10 | `fc5456a` | corrigir indicador público de disponibilidade e título de salas


## Atualização posterior — comparação de notas

A implementação adicional de CVSS 3.1 × 4.0, os resultados de 151 testes e as
correções numéricas posteriores estão em [COMPARACAO_CVSS.md](COMPARACAO_CVSS.md).
