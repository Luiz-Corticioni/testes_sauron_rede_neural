# Laboratório Sentinela: demonstração com produtos reais e painel

## Escopo e utilização

Esta é uma variação experimental da interface, criada em branch de laboratório. Na visão geral, um superusuário pode escolher **Preparar uma demonstração fictícia → Carregar produtos e CVEs reais**. A carga também pode ser feita por `python manage.py seed_demo --empresa-realista`. Exige inventário vazio; não substitui nem apaga dados existentes. A opção anterior continua disponível. O cenário contém 31 ativos simulados, 16 incidências simuladas, quatro CVEs públicas e relações com pesos hipotéticos.

Os produtos, os avisos e as notas CVSS indicadas existem. A empresa, os dispositivos, suas versões instaladas, a configuração dos serviços e as incidências são hipóteses para demonstração; não existe descoberta ou scanner implícito. As incidências aparecem abertas para alimentar o modelo, mas suas observações as identificam como SIMULAÇÃO. Nenhuma ocorrência deve ser tratada como detecção real. A ausência de ocorrência nos demais ativos não prova segurança. O estado de KEV e os valores EPSS não foram importados ou atualizados por esta carga.

## Associações demonstrativas e suas condições

| Produto e versão hipotéticos | CVE e fonte pública | Condição que deve ser verificada em uma rede real |
| --- | --- | --- |
| Cisco Catalyst 9300, IOS XE 17.9.3 | [CVE-2023-20198 — Cisco](https://sec.cloudapps.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-iosxe-webui-privesc-j22SaA4z), CVSS 3.1 10,0 | Interface web HTTP/HTTPS habilitada; verificar versão e exposição conforme aviso. |
| Huawei S12700, V200R010C00 | [CVE-2019-5285 — Huawei](https://www.huawei.com/en/psirt/security-advisories/2019/huawei-sa-20190522-01-switch-en), CVSS 3.0 7,5 | Confirmar versão, correção e possibilidade de acesso à rede. |
| Palo Alto PA-3220, PAN-OS 10.2.8 | [CVE-2024-3400 — Palo Alto](https://security.paloaltonetworks.com/CVE-2024-3400), [CVSS 3.1 NVD](https://nvd.nist.gov/vuln/detail/cve-2024-3400) 10,0 | Confirmar hotfix e configuração do gateway ou portal GlobalProtect. |
| Apache HTTP Server 2.4.50 | [CVE-2021-42013 — Apache](https://httpd.apache.org/security/vulnerabilities_24.html#CVE-2021-42013), [NVD](https://nvd.nist.gov/vuln/detail/cve-2021-42013), CVSS 3.1 9,8 | Conferir diretórios e configuração; execução remota requer CGI, conforme aviso. |

Os links e condições foram consultados em 17/11/2026. Os avisos podem mudar; os dados incluídos são um recorte estático, não sincronização contínua. Para um inventário real, conferir identificação, versão, patches, configuração e aplicabilidade antes de confirmar a incidência.

## Painel e identidade

O painel mostra ativos distintos com incidências pendentes, distribuição das vulnerabilidades por CVSS base e composição do inventário por tipo. Os valores são consultas do banco com o mesmo escopo e permissões do painel; há links para as listas e para as análises FAIR de 30 dias. As barras indicam contagens, não tendências históricas, probabilidade de exploração ou previsão de perdas. Os critérios de ordenação de prioridades podem considerar pontuação ambiental; o texto foi corrigido para não prometer ordenação exclusiva pela redução estimada.

A imagem atmosférica foi gerada para este experimento e é decorativa. O painel usa HTML, CSS e SVG locais, sem CDN ou serviço pago. A interface preserva movimento reduzido, rótulos, valores textuais, MFA e permissões; isso não substitui uma auditoria de acessibilidade. A estética é uma proposta própria inspirada de forma geral em fantasia sombria, sem reproduzir imagens ou marcas dos jogos citados.

## Verificações

Os testes de integração verificam os avisos, versões e associações, o cálculo de risco com o cenário, a recusa a dados existentes, as contagens e o filtro de severidade. A suíte local passou com 510 testes, assim como a análise estática, testes JavaScript e coleta dos arquivos estáticos. A prévia foi examinada em desktop e em viewport 390 × 844; o filtro de severidade foi seguido até a lista correspondente. O CI da branch deve ser consultado para a execução em outros ambientes. Não foi feita varredura real de rede nem implantado qualquer ativo de terceiros.
