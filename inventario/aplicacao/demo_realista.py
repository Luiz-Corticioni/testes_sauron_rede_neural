"""Aurora: inventário hipotético, avisos públicos e fotografia EPSS datada."""
import hashlib
import json
from datetime import date

from django.utils import timezone
from inventario.models import Ativo, Dependencia, Incidencia, ObservacaoEPSS, Sala, Vulnerabilidade

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
    ('CVE-2021-44790', 'RCE', 9.8, '3.1', 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
     'Apache: overflow no processamento multipart do mod_lua.',
     'https://httpd.apache.org/security/vulnerabilities_24.html#CVE-2021-44790',
     'Hipótese: mod_lua e script que usa r:parsebody estão habilitados.'),
    ('CVE-2021-44224', 'OUTRA', 8.2, '3.1', 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:L/A:H',
     'Apache: falha em configurações de proxy de encaminhamento.',
     'https://httpd.apache.org/security/vulnerabilities_24.html#CVE-2021-44224',
     'Hipótese: proxy de encaminhamento habilitado; impacto depende da configuração.'),
    ('CVE-2022-22720', 'OUTRA', 9.8, '3.1', 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
     'Apache: HTTP request smuggling no tratamento do corpo da requisição.',
     'https://httpd.apache.org/security/vulnerabilities_24.html#CVE-2022-22720',
     'Hipótese: servidor sem correção e cadeia HTTP vulnerável.'),
    ('CVE-2022-23943', 'RCE', 9.8, '3.1', 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
     'Apache: escrita fora dos limites no mod_sed.',
     'https://httpd.apache.org/security/vulnerabilities_24.html#CVE-2022-23943',
     'Hipótese: mod_sed habilitado e dados não confiáveis processados.'),
)

# FIRST API, consulta de 2026-11-27; é uma fotografia, não uma previsão local.
EPSS_DATA = date(2026, 11, 27)
EPSS_FOTOGRAFIA = {
    'CVE-2023-20198': (.70922, .99571), 'CVE-2019-5285': (.01656, .77029),
    'CVE-2024-3400': (.93034, .99893), 'CVE-2021-42013': (.99964, .99987),
    'CVE-2021-44790': (.96527, .99925), 'CVE-2021-44224': (.82295, .99769),
    'CVE-2022-22720': (.18496, .97828), 'CVE-2022-23943': (.10240, .96418),
}

FUNCOES = {
    'Switch de núcleo': ('Núcleo primário', 'Núcleo secundário', 'Núcleo filial', 'Núcleo laboratório'),
    'Switch de distribuição': ('Distribuição escritório', 'Distribuição datacenter', 'Distribuição filial', 'Distribuição laboratório'),
    'Firewall de borda': ('Borda matriz', 'Borda contingência', 'Borda filial', 'Borda laboratório'),
    'Servidor web': ('Portal clientes', 'Portal parceiros', 'Intranet', 'Portal de suporte'),
    'Servidor de aplicações': ('Pedidos', 'Faturamento', 'Autenticação'),
    'Banco de dados': ('Pedidos', 'Faturamento', 'Identidades'),
    'Proxy reverso': ('Gateway clientes', 'Gateway parceiros', 'Gateway interno'),
    'Serviço de DNS': ('DNS interno primário', 'DNS interno secundário', 'DNS filial'),
    'Notebook de operações': ('Administração de redes', 'Administração de sistemas'),
}


def carregar_fotografia(vulnerabilidade):
    """Registra a data real da fonte; nunca promove uma fotografia antiga a atual."""
    if EPSS_DATA > timezone.localdate():
        return
    valor, percentil = EPSS_FOTOGRAFIA[vulnerabilidade.cve_id]
    dados = {'epss': valor, 'percentil': percentil, 'data': EPSS_DATA.isoformat(), 'modelo': ''}
    assinatura = hashlib.sha256(json.dumps(dados, sort_keys=True, allow_nan=False).encode()).hexdigest()
    observacao = ObservacaoEPSS.objects.create(cve_id=vulnerabilidade.cve_id, data=EPSS_DATA,
        epss=valor, percentil=percentil, assinatura=assinatura)
    vulnerabilidade.epss = valor
    vulnerabilidade.epss_data = EPSS_DATA
    vulnerabilidade.epss_observacao = observacao
    vulnerabilidade.save(update_fields=['epss', 'epss_data', 'epss_observacao'])


def criar_empresa():
    sala = Sala.objects.create(id='SALA-AURORA', nome='Aurora — inventário simulado', tipos_permitidos=list('123456789'))
    vulns = {}
    for numero, (cve, categoria, cvss, versao, vetor, descricao, fonte, condicao) in enumerate(AVISOS, 1):
        vulns[cve] = Vulnerabilidade.objects.create(id=f'VUL-REAL-{numero:04}', cve_id=cve, categoria=categoria, cvss=cvss,
            cvss_versao=versao, cvss_vetor=vetor, descricao=descricao, fonte=FONTE, referencias=[fonte])
        carregar_fotografia(vulns[cve])
    perfis = [
        ('4', 'Switch de núcleo', 'Cisco', 'Catalyst 9300', 'IOS XE', '17.9.3', 'CVE-2023-20198', 4),
        ('4', 'Switch de distribuição', 'Huawei', 'S12700', 'VRP', 'V200R010C00', 'CVE-2019-5285', 4),
        ('5', 'Firewall de borda', 'Palo Alto Networks', 'PA-3220', 'PAN-OS', '10.2.8', 'CVE-2024-3400', 4),
        ('7', 'Servidor web', 'Apache', 'HTTP Server', 'httpd', '2.4.50', 'CVE-2021-42013', 4),
        ('1', 'Servidor de aplicações', 'Dell', 'PowerEdge R750', 'Linux', '', None, 3),
        ('8', 'Banco de dados', 'PostgreSQL', 'PostgreSQL', 'PostgreSQL', '', None, 3),
        ('7', 'Proxy reverso', 'F5', 'NGINX', 'NGINX', '', None, 3),
        ('9', 'Serviço de DNS', 'ISC', 'BIND 9', 'BIND', '', None, 3),
        ('2', 'Notebook de operações', 'Lenovo', 'ThinkPad T14', 'Windows', '', None, 2),
    ]
    ativos = []
    condicoes = {item[0]: item[-1] for item in AVISOS}
    for tipo, nome, fabricante, modelo, software, versao, cve, quantidade in perfis:
        for i in range(quantidade):
            numero = len(ativos) + 1
            funcao = FUNCOES[nome][i]
            equipe = 'Redes' if tipo in ('4', '5') else 'Aplicações' if tipo in ('7', '8', '9') else 'Infraestrutura'
            ativo = Ativo.objects.create(tipo=tipo, nome=f'DEMO · {nome} — {funcao}', fabricante=fabricante,
                modelo=modelo, sala=sala, sistema_operacional=software, versao=versao, responsavel=f'Equipe {equipe} (fictícia)',
                ip=f'192.0.2.{numero}', exposto_internet=tipo in ('5', '7') and i == 0,
                criticidade=4 if cve else 3, atributos={'origem': 'demonstração fictícia',
                    'configuracao': 'hipótese', 'funcao': funcao, 'ambiente': 'produção simulada',
                    'responsavel_operacional': equipe})
            ativos.append(ativo)
            if cve:
                Incidencia.objects.create(id=f'INC-AURORA-{len(ativos):03}', ativo=ativo, vulnerabilidade=vulns[cve],
                    versao_afetada=versao, observacoes='SIMULAÇÃO; não é detecção real. ' + condicoes[cve])
                if cve == 'CVE-2021-42013':
                    for adicional in ('CVE-2021-44790', 'CVE-2021-44224', 'CVE-2022-22720', 'CVE-2022-23943'):
                        Incidencia.objects.create(id=f'INC-AURORA-{len(ativos):03}-{adicional[-5:]}',
                            ativo=ativo, vulnerabilidade=vulns[adicional], versao_afetada=versao,
                            observacoes='SIMULAÇÃO; não é detecção real. ' + condicoes[adicional])
    # Pesos são exemplos e o grafo não comprova propagação nem conectividade real.
    for i, ativo in enumerate(ativos[4:], start=4):
        Dependencia.objects.create(dependente=ativo, fornecedor=ativos[i % 4], peso=.16,
            descricao='Relação hipotética para demonstração')
        if i >= 8:
            Dependencia.objects.create(dependente=ativo, fornecedor=ativos[i-4], peso=.12,
                descricao='Relação hipotética para demonstração')
