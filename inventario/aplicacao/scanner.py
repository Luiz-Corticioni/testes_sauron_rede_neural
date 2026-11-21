"""Perfil restrito de relatório Trivy JSON, sem executar scanner ou consultar rede."""
import hashlib
import json
import re
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import DatabaseError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from inventario.aplicacao.documentos import autorizar
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import Ativo, RelatorioScanner, RevisaoAchadoScanner

LIMITE = 2 * 1024 * 1024


def extrair(conteudo):
    if not isinstance(conteudo, bytes) or len(conteudo) > LIMITE:
        raise ValidationError("Arquivo inválido ou maior que 2 MB.")
    try:
        doc = json.loads(conteudo.decode("utf-8"))
        if not isinstance(doc, dict) or doc.get("SchemaVersion") != 2 or not isinstance(doc.get("Results", []), list):
            raise ValidationError("Esperado relatório Trivy JSON SchemaVersion 2.")
        data = parse_datetime(doc.get("CreatedAt", ""))
        if data is None or timezone.is_naive(data):
            raise ValidationError("O relatório deve informar CreatedAt com fuso horário.")
        achados, ignorados = set(), 0
        resultados = doc.get("Results", [])
        if len(resultados) > 500:
            raise ValidationError("Muitos grupos de resultados.")
        total = 0
        for grupo in resultados:
            if not isinstance(grupo, dict) or not isinstance(grupo.get("Vulnerabilities", []), list):
                raise ValidationError("Grupo de vulnerabilidades inválido.")
            for item in grupo.get("Vulnerabilities", []):
                total += 1
                if total > 5000 or not isinstance(item, dict):
                    raise ValidationError("Limite de 5.000 achados excedido ou achado inválido.")
                cve, nome, versao = (item.get(k) for k in ("VulnerabilityID", "PkgName", "InstalledVersion"))
                if not all(isinstance(v, str) for v in (cve, nome, versao)) or not re.fullmatch(r"CVE-\d{4}-\d{4,}", cve) or not nome or not versao or len(nome) > 200 or len(versao) > 200:
                    ignorados += 1
                    continue
                achados.add((cve, nome, versao))
        dados = [{"cve": c, "pacote": n, "versao": v} for c, n, v in sorted(achados)]
        assinatura = hashlib.sha256(json.dumps({"data": data.isoformat(), "achados": dados, "ignorados": ignorados}, sort_keys=True).encode()).hexdigest()
        return data, dados, ignorados, assinatura
    except (UnicodeDecodeError, ValueError, TypeError, RecursionError) as erro:
        raise ValidationError("Relatório JSON inválido.") from erro


def extrair_relatorio(conteudo, formato='trivy', observado_em=''):
    if formato == 'trivy':
        return extrair(conteudo)
    if formato == 'osv':
        from inventario.aplicacao.scanner_osv import extrair_osv
        return extrair_osv(conteudo, observado_em)
    raise ValidationError('Formato de scanner não suportado.')


def gravar(ativo_id, escopo, origem, conteudo, usuario, formato='trivy', observado_em=''):
    from inventario.infraestrutura.estado_consultas_fontes import registrar_estado

    try:
        resultado = _gravar(ativo_id, escopo, origem, conteudo, usuario, formato, observado_em)
    except (ValidationError, ObjectDoesNotExist, DatabaseError, OSError):
        registrar_estado("scanner", "falha")
        raise
    transaction.on_commit(lambda: registrar_estado("scanner", "resposta"))
    return resultado


@transaction.atomic
def _gravar(ativo_id, escopo, origem, conteudo, usuario, formato='trivy', observado_em=''):
    usuario = autorizar(usuario)
    data, achados, ignorados, assinatura = extrair_relatorio(conteudo, formato, observado_em)
    if formato == 'osv':
        origem = f'OSV-Scanner: {origem}'
        if len(origem) > 200:
            raise ValidationError('A origem é muito longa; use até 187 caracteres para OSV-Scanner.')
    travar_escrita()
    usuario = autorizar(usuario)
    ativo = Ativo.objects.get(pk=ativo_id)
    if ativo.status in ("INATIVO", "BAIXADO"):
        raise ValidationError("Selecione um ativo ativo ou em manutenção.")
    with usar_usuario(usuario):
        relatorio, novo = RelatorioScanner.objects.get_or_create(ativo=ativo, escopo=escopo, origem=origem, sha256=assinatura,
            defaults={"observado_em": data, "achados": achados, "ignorados": ignorados, "importado_por": usuario})
        registrar_evento("IMPORTAR_SCANNER", "RelatorioScanner", relatorio.pk, {"novo": novo, "achados": len(achados), "ignorados": ignorados})
    return relatorio, novo


@transaction.atomic
def revisar(relatorio_id, indice, classificacao, justificativa, usuario):
    usuario = autorizar(usuario)
    travar_escrita()
    usuario = autorizar(usuario)
    relatorio = RelatorioScanner.objects.get(pk=relatorio_id)
    if type(indice) is not int or not 0 <= indice < len(relatorio.achados):
        raise ValidationError("Achado não encontrado.")
    revisao = RevisaoAchadoScanner(relatorio=relatorio, indice=indice, classificacao=classificacao,
                                   justificativa=justificativa, autor=usuario)
    revisao.full_clean()
    with usar_usuario(usuario):
        revisao.save()
        registrar_evento("REVISAR_SCANNER", "RelatorioScanner", relatorio.pk,
                         {"indice": indice, "classificacao": classificacao, "revisao": revisao.pk})
    return revisao
