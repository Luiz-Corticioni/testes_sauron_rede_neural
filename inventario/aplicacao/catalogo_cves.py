"""Autocomplete local e consultas explícitas à NVD, com origem e CVSS verificável."""

from datetime import datetime, timezone
import json
import logging
import time

from django.conf import settings

from inventario.dominio.autocomplete import APELIDOS, normalizar_texto, normalizar_cve, sugerir
from inventario.infraestrutura.cve_client import CVE_RE, TTL, CisaKevClient, IntegracaoCVEError, NvdClient
from inventario.matematica.cvss import CalculadoraCVSS31
from inventario.dominio.comparacao_cvss import comparar_notas
from inventario.models import Vulnerabilidade

LOGGER = logging.getLogger(__name__)


def resumo_cvss(cve):
    """Mantém o contrato legado; cada versão é selecionada com publicador explícito."""
    from inventario.dominio.comparacao_cvss import selecionar_metrica
    resultado = {"score":None, "versao":"", "vetor":"", "fonte":"",
                 "score_recalculado":None, "consistente":None, "aviso":""}
    for versao in ("3.1", "3.0", "4.0", "2.0"):
        metrica=selecionar_metrica(cve,versao)
        if metrica["nota"] is None:
            continue
        resultado.update(score=metrica["nota"], versao=versao, vetor=metrica["vetor"], fonte=metrica["publicador"])
        if versao=="3.1" and metrica["utilizavel"]:
            calculado=CalculadoraCVSS31.calcular(metrica["vetor_base"]).score
            resultado.update(score_recalculado=calculado, consistente=calculado==metrica["nota"])
            if not resultado["consistente"]:
                resultado["aviso"]="A nota recebida diverge do recálculo 3.1. Revise antes de cadastrar."
        else:
            resultado["aviso"]=metrica["aviso"] or "Nota da fonte; recálculo local cobre a base CVSS 3.1."
        return resultado
    resultado["aviso"]="A fonte não informou uma nota utilizável; ausência não equivale a zero."
    return resultado


def resumo_cve(cve):
    descricoes = cve.get('descriptions', [])
    if not isinstance(descricoes, list):
        descricoes = []
    validas = [d for d in descricoes if isinstance(d, dict) and isinstance(d.get('value'), str)]
    descricao = next((d['value'] for d in validas if d.get('lang') == 'en'),
                     validas[0]['value'] if validas else 'Sem descrição disponível.')
    return {'id': cve['id'], 'titulo': descricao[:160], 'descricao': descricao[:5000],
            'publicada_em': cve.get('published', ''), 'alterada_em': cve.get('lastModified', ''),
            'status': cve.get('vulnStatus', ''), 'url': f"https://nvd.nist.gov/vuln/detail/{cve['id']}",
            'cvss': resumo_cvss(cve), 'comparacao_cvss': comparar_notas(cve)}


def preparar_importacao(cve_id):
    """Reaproveita a consulta explícita anterior; abrir formulário não acessa a internet."""
    from inventario.aplicacao.cadastros import proximo_id_vulnerabilidade

    cve = NvdClient(settings.NVD_API_KEY, settings.DATA_DIR/'cache'/'nvd').buscar(
        normalizar_cve(cve_id)
    )
    if cve.get("vulnStatus") == "Rejected":
        raise IntegracaoCVEError("CVE rejeitada pela NVD; importação recusada.")
    resumo = resumo_cve(cve)
    dados = {
        'id': proximo_id_vulnerabilidade('OUTRA'), 'cve_id': resumo['id'],
        'descricao': resumo['descricao'], 'categoria': 'OUTRA', 'cvss': resumo['cvss']['score'],
        'cvss_versao': resumo['cvss']['versao'] or '3.1', 'cvss_vetor': resumo['cvss']['vetor'],
        'fonte': 'NVD', 'publicada_em': resumo['publicada_em'][:10] or None,
    }
    return dados, ('Baixa confiança: Awaiting Analysis. ' if cve.get('vulnStatus') == 'Awaiting Analysis' else '') + resumo['cvss']['aviso']


def candidatos_locais():
    """Une banco, KEV e caches de CVEs baixadas; falha de cache não vira erro 500."""
    itens, avisos = {}, []
    for v in Vulnerabilidade.objects.filter(cve_id__isnull=False).exclude(cve_id='').values('cve_id', 'descricao', 'cvss')[:10000]:
        if CVE_RE.fullmatch(v['cve_id']):
            itens[v['cve_id']] = {'id': v['cve_id'], 'titulo': v['descricao'][:160],
                                  'descricao': v['descricao'][:1500], 'origem': 'inventário', 'score': v['cvss']}
    try:
        dados, origem = CisaKevClient(settings.DATA_DIR/'cache_kev.json').carregar()
        if 'expirado' in origem:
            avisos.append('Catálogo KEV local expirado; consulte a internet para atualizar.')
        for v in dados['vulnerabilities']:
            itens.setdefault(v['cveID'], {'id': v['cveID'], 'titulo': v.get('vulnerabilityName', '')[:160],
                 'descricao': str(v.get('shortDescription', ''))[:1500], 'produto': str(v.get('product', '')),
                 'fabricante': str(v.get('vendorProject', '')), 'origem': origem, 'score': None})
    except IntegracaoCVEError:
        avisos.append('Sem catálogo KEV local válido. A busca na NVD continua disponível.')
    pasta = settings.DATA_DIR/'cache'/'nvd'
    for caminho in sorted(pasta.glob('CVE-*.json'))[:2000]:
        try:
            if caminho.stat().st_size > 2*1024*1024:
                continue
            envelope = json.loads(caminho.read_text(encoding='utf-8'))
            cve = envelope['cve']
            if not isinstance(cve, dict) or not CVE_RE.fullmatch(str(cve.get('id', ''))):
                continue
            resumo = resumo_cve(cve)
            resumo.update(origem='cache NVD', score=resumo['cvss']['score'],
                          desatualizado=not 0 <= time.time()-float(envelope['ts']) < TTL)
            # Mantém o título reconhecível do KEV, se existente, e inclui a descrição NVD.
            if cve['id'] in itens:
                resumo['titulo'] = itens[cve['id']]['titulo'] or resumo['titulo']
            itens[cve['id']] = resumo
        except (OSError, ValueError, KeyError, TypeError):
            LOGGER.warning('Cache NVD inválido ignorado no autocomplete: %s', caminho.name)
    for apelido, id_ in APELIDOS.items():
        if id_ in itens:
            itens[id_]['apelidos'] = apelido
            itens[id_]['titulo'] = f"{apelido.title()} · {itens[id_]['titulo']}"
    return list(itens.values()), avisos


def autocomplete_cves(termo, limite=8):
    if not isinstance(termo, str) or len(termo) > 120:
        raise ValueError('Use uma busca de até 120 caracteres.')
    if len(termo.strip()) < 2:
        return {'sugestoes': [], 'origem': 'catálogo local', 'avisos': [], 'normalizado': normalizar_cve(termo)}
    candidatos, avisos = candidatos_locais()
    return {'sugestoes': sugerir(termo, candidatos, limite), 'origem': 'catálogo local',
            'avisos': avisos, 'normalizado': normalizar_cve(termo)}


def consultar_internet(termo, forcar=False):
    """Identificador completo: consulta única. Nome de produto: busca por palavras."""
    if not isinstance(termo, str) or not 2 <= len(termo.strip()) <= 120:
        raise ValueError('Informe entre 2 e 120 caracteres.')
    inicio = time.time()
    cliente = NvdClient(settings.NVD_API_KEY, settings.DATA_DIR/'cache'/'nvd')
    normalizado = APELIDOS.get(normalizar_texto(termo), normalizar_cve(termo))
    if CVE_RE.fullmatch(normalizado):
        cve = cliente.atualizar(normalizado, forcar=forcar)
        envelope = json.loads(cliente._caminho(normalizado)[1].read_text(encoding='utf-8'))
        instante = float(envelope['ts'])
        dados = {'cves': [cve], 'total': 1, 'truncado': False}
    else:
        dados, instante = cliente.pesquisar(termo.strip(), forcar=forcar)
    return {'resultados': [resumo_cve(cve) for cve in dados['cves']],
            'total': dados['total'], 'truncado': dados['truncado'],
            'origem': 'NVD pela internet' if instante >= inicio else 'cache NVD',
            'consultado_em': datetime.fromtimestamp(instante, timezone.utc).isoformat(),
            'normalizado': normalizado, 'aviso': 'Resultado externo não confirma que seu ativo esteja vulnerável.'}
