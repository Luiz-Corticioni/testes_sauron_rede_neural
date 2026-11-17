"""Inventário hipotético baseado em produtos e avisos públicos reais, sem coleta externa."""
from inventario.models import Ativo, Dependencia, Incidencia, Sala, Vulnerabilidade

FONTE = 'Aurora fictícia - avisos reais'
AVISOS = (
    ('CVE-2023-20198', 'PRIV', 10.0, '3.1', 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H',
     'Cisco IOS XE: elevação de privilégio na interface web.',
     'https://sec.cloudapps.cisco.com/security/center/content/CiscoSecurityAdvisory/cisco-sa-iosxe-webui-privesc-j22SaA4z',
     'Cenário supõe interface HTTP/HTTPS de gerenciamento habilitada; confirmação dependeria da configuração e versão reais.'),
    ('CVE-2019-5285', 'DOS', 7.5, '3.0', '', 'Huawei S Series: negação de serviço por pacotes especialmente construídos.',
     'https://www.huawei.com/en/psirt/security-advisories/2019/huawei-sa-20190522-01-switch-en',
     'Cenário supõe S12700 V200R010C00 sem correção; a condição exige acesso à rede.'),
    ('CVE-2024-3400', 'INJ', 10.0, '3.1', 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H',
     'PAN-OS: injeção de comandos no GlobalProtect.', 'https://security.paloaltonetworks.com/CVE-2024-3400',
     'Cenário supõe PAN-OS 10.2.8 sem hotfix e gateway ou portal GlobalProtect configurado.'),
    ('CVE-2021-42013', 'RCE', 9.8, '3.1', 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
     'Apache HTTP Server: path traversal e possível execução remota.',
     'https://httpd.apache.org/security/vulnerabilities_24.html#CVE-2021-42013',
     'Cenário supõe Apache 2.4.50, diretórios sem proteção adequada e CGI habilitado para execução de código.'),
)


def criar_empresa():
    sala = Sala.objects.create(id='SALA-AURORA', nome='Aurora — inventário simulado', tipos_permitidos=list('123456789'))
    vulns = {}
    for numero, (cve, categoria, cvss, versao, vetor, descricao, fonte, condicao) in enumerate(AVISOS, 1):
        vulns[cve] = Vulnerabilidade.objects.create(id=f'VUL-REAL-{numero:04}', cve_id=cve, categoria=categoria, cvss=cvss,
            cvss_versao=versao, cvss_vetor=vetor, descricao=descricao, fonte=FONTE, referencias=[fonte])
    perfis = [
        ('4', 'Switch de núcleo', 'Cisco', 'Catalyst 9300', 'IOS XE', '17.9.3', 'CVE-2023-20198', 4),
        ('4', 'Switch de distribuição', 'Huawei', 'S12700', 'VRP', 'V200R010C00', 'CVE-2019-5285', 4),
        ('5', 'Firewall de borda', 'Palo Alto Networks', 'PA-3220', 'PAN-OS', '10.2.8', 'CVE-2024-3400', 4),
        ('7', 'Servidor web', 'Apache', 'HTTP Server', 'httpd', '2.4.50', 'CVE-2021-42013', 4),
        ('1', 'Servidor de aplicações', 'Dell', 'PowerEdge R750', 'Linux', '', None, 3),
        ('8', 'Banco de dados', 'PostgreSQL', 'PostgreSQL', 'PostgreSQL', '', None, 3),
        ('7', 'Proxy reverso', 'F5', 'NGINX', 'NGINX', '', None, 3),
        ('9', 'Serviço de DNS', 'ISC', 'BIND 9', 'BIND', '', None, 3),
        ('2', 'Notebook de operações', 'Lenovo', 'ThinkPad T14', 'Windows', '', None, 3),
    ]
    ativos = []
    condicoes = {item[0]: item[-1] for item in AVISOS}
    for tipo, nome, fabricante, modelo, software, versao, cve, quantidade in perfis:
        for i in range(quantidade):
            ativo = Ativo.objects.create(tipo=tipo, nome=f'DEMO · {nome} {i+1:02}', fabricante=fabricante,
                modelo=modelo, sala=sala, sistema_operacional=software, versao=versao, responsavel='Equipe fictícia',
                criticidade=4 if cve else 3, atributos={'origem': 'demonstração fictícia', 'configuracao': 'hipótese'})
            ativos.append(ativo)
            if cve:
                Incidencia.objects.create(id=f'INC-AURORA-{len(ativos):03}', ativo=ativo, vulnerabilidade=vulns[cve],
                    versao_afetada=versao, observacoes='SIMULAÇÃO; não é detecção real. ' + condicoes[cve])
    # Pesos são exemplos e o grafo não comprova propagação nem conectividade real.
    for i, ativo in enumerate(ativos[4:], start=4):
        Dependencia.objects.create(dependente=ativo, fornecedor=ativos[i % 4], peso=.16,
            descricao='Relação hipotética para demonstração')
        if i >= 8:
            Dependencia.objects.create(dependente=ativo, fornecedor=ativos[i-4], peso=.12,
                descricao='Relação hipotética para demonstração')
