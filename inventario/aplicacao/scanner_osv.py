"""Perfil restrito de saída JSON do OSV-Scanner; importação offline."""
import hashlib
import json
import re
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from inventario.aplicacao.scanner import LIMITE


def extrair_osv(conteudo, observado_em):
    if not isinstance(conteudo, bytes) or len(conteudo) > LIMITE:
        raise ValidationError('Arquivo inválido ou maior que 2 MB.')
    try:
        data = parse_datetime(observado_em) if isinstance(observado_em, str) else None
    except ValueError as erro:
        raise ValidationError('Data de observação inválida.') from erro
    if data is None or timezone.is_naive(data):
        raise ValidationError('Informe a data da varredura com fuso, por exemplo 2026-11-18T10:30:00-03:00.')
    try:
        documento = json.loads(conteudo.decode('utf-8'))
        if not isinstance(documento, dict) or not isinstance(documento.get('results'), list):
            raise ValidationError('Esperado JSON do OSV-Scanner com results como lista.')
        if len(documento['results']) > 500:
            raise ValidationError('Muitos grupos de resultados.')
        achados, ignorados, total = set(), 0, 0
        for grupo in documento['results']:
            if not isinstance(grupo, dict) or not isinstance(grupo.get('packages'), list):
                raise ValidationError('Grupo de pacotes inválido.')
            for registro in grupo['packages']:
                if not isinstance(registro, dict) or not isinstance(registro.get('package'), dict) or not isinstance(registro.get('vulnerabilities', []), list):
                    raise ValidationError('Registro de pacote inválido.')
                pacote = registro['package']
                nome, versao, ecossistema = pacote.get('name'), pacote.get('version'), pacote.get('ecosystem')
                for vulnerabilidade in registro.get('vulnerabilities', []):
                    total += 1
                    if total > 5000 or not isinstance(vulnerabilidade, dict):
                        raise ValidationError('Limite de 5.000 achados excedido ou achado inválido.')
                    aliases = vulnerabilidade.get('aliases', [])
                    if not isinstance(aliases, list) or len(aliases) > 1000 or not all(isinstance(a, str) and len(a) <= 200 for a in aliases):
                        raise ValidationError('Lista de aliases inválida.')
                    identidade = vulnerabilidade.get('id')
                    if not isinstance(identidade, str) or not identidade or len(identidade) > 200:
                        raise ValidationError('Identificador de vulnerabilidade inválido.')
                    ids = [a for a in [identidade, *aliases] if isinstance(a, str) and re.fullmatch(r'CVE-\d{4}-\d{4,}', a)]
                    if not ids or not all(isinstance(v, str) and 0 < len(v) <= 200 for v in (nome, versao, ecossistema)) or len(ecossistema) + len(nome) + 1 > 200:
                        ignorados += 1
                        continue
                    for cve in ids:
                        achados.add((cve, f'{ecossistema}:{nome}', versao))
                        if len(achados) > 5000:
                            raise ValidationError('Limite de 5.000 achados únicos excedido.')
        dados = [{'cve': c, 'pacote': n, 'versao': v} for c, n, v in sorted(achados)]
        resumo = {'formato': 'OSV', 'data': data.isoformat(), 'achados': dados, 'ignorados': ignorados}
        assinatura = hashlib.sha256(json.dumps(resumo, sort_keys=True).encode()).hexdigest()
        return data, dados, ignorados, assinatura
    except (UnicodeDecodeError, ValueError, TypeError, RecursionError) as erro:
        raise ValidationError('Relatório JSON inválido.') from erro
