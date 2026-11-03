"""Busca determinística: normalização, prefixos e distância de edição limitada.

Não inventa CVEs. Os candidatos são registros fornecidos pelo catálogo.
Um identificador apenas normalizado continua dependendo de consulta à NVD.
"""

import re
import unicodedata

# Apelidos conhecidos ajudam a achar o registro; nunca substituem sua validação.
APELIDOS = {'log4shell': 'CVE-2021-44228'}


def normalizar_texto(texto):
    texto = unicodedata.normalize('NFKD', str(texto).casefold())
    return ' '.join(''.join(c for c in texto if not unicodedata.combining(c)).split())


def normalizar_cve(texto):
    """Aceita CVE 2021 44228, cve202144228 e 2021-44228 sem alterar dígitos."""
    texto = str(texto).strip()
    compacto = re.sub(r'[\s_\-]', '', texto.upper())
    if compacto.startswith('CVE'):
        compacto = compacto[3:]
    if re.fullmatch(r'[0-9]{8,27}', compacto):
        return f'CVE-{compacto[:4]}-{compacto[4:]}'
    return texto.upper()


def distancia_limitada(a, b, limite=2):
    """Levenshtein com saída antecipada; custo limitado pelo tamanho da entrada."""
    if abs(len(a)-len(b)) > limite:
        return limite + 1
    anterior = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        atual = [i]
        for j, cb in enumerate(b, 1):
            atual.append(min(atual[-1]+1, anterior[j]+1, anterior[j-1]+(ca != cb)))
        if min(atual) > limite:
            return limite + 1
        anterior = atual
    return anterior[-1]


def sugerir(termo, candidatos, limite=8):
    """Ordena identidade, prefixo, palavras e erro de digitação, nessa ordem."""
    if not isinstance(termo, str) or len(termo) > 120:
        raise ValueError('Use uma busca de até 120 caracteres.')
    consulta = normalizar_texto(termo)
    if len(consulta) < 2:
        return []
    id_busca = normalizar_cve(consulta)
    compacto = re.sub(r'[^a-z0-9]', '', consulta)
    tokens = consulta.split()
    encontrados = []
    for candidato in candidatos:
        id_ = candidato['id']
        texto = normalizar_texto(' '.join(str(candidato.get(c, '')) for c in
                                        ('id', 'titulo', 'descricao', 'produto', 'fabricante', 'apelidos')))
        id_compacto = re.sub(r'[^a-z0-9]', '', id_.casefold())
        palavras = set(re.findall(r'[a-z0-9]+', texto[:3000]))
        pontos = 0
        motivo = 'palavras'
        if id_ == id_busca:
            pontos, motivo = 100, 'identificador'
        elif id_compacto.startswith(compacto) or (compacto.isdigit() and id_compacto[3:].startswith(compacto)):
            pontos, motivo = 90, 'prefixo'
        elif all(token in texto for token in tokens):
            pontos = 80
        elif compacto.startswith('cve') and len(compacto) >= 10 and distancia_limitada(compacto, id_compacto) <= 2:
            pontos, motivo = 60, 'digitação próxima'
        elif all(len(token) >= 4 and any(distancia_limitada(token, p) <= 1 for p in palavras) for token in tokens):
            pontos, motivo = 50, 'digitação próxima'
        if pontos:
            encontrados.append((pontos, id_, dict(candidato, correspondencia=motivo)))
    encontrados.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in encontrados[:max(1, min(limite, 20))]]
