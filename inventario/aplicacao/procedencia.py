"""Resumo de evidências existentes, sem inferir a validade das informações."""
from django.db.models import Q
from django.utils import timezone

from inventario.aplicacao.documentos import LEITURA as LEITURA_DOCUMENTOS
from inventario.aplicacao.fair import LEITURA as LEITURA_FAIR
from inventario.aplicacao.relacoes import LEITURA as LEITURA_RELACOES
from inventario.models import CenarioFAIR, DocumentoInventario, RelacaoAtivos, RelatorioScanner


def evidencias_ativo(ativo, usuario):
    """Somente dados autorizados; ausência e falta de permissão são distintas."""
    resultado = {'cadastro_atualizado_em': ativo.atualizado_em,
                 'cadastro_criado_em': ativo.criado_em,
                 'origem_demonstracao': ativo.atributos.get('origem') == 'demonstração fictícia' if isinstance(ativo.atributos, dict) else False}
    if usuario.has_perms(LEITURA_DOCUMENTOS):
        resultado['documentos'] = list(DocumentoInventario.objects.filter(ativo=ativo)
            .only('id', 'tipo', 'origem', 'escopo', 'importado_em').order_by('-importado_em', '-pk')[:5])
        resultado['scanners'] = list(RelatorioScanner.objects.filter(ativo=ativo)
            .only('id', 'origem', 'escopo', 'observado_em', 'importado_em').order_by('-observado_em', '-pk')[:5])
    if usuario.has_perms(LEITURA_RELACOES):
        resultado['relacoes'] = list(RelacaoAtivos.objects.filter(Q(origem=ativo) | Q(destino=ativo))
            .only('id', 'tipo', 'fonte', 'observada_em', 'revisar_em', 'vigente')
            .order_by('-observada_em', '-pk')[:5])
        resultado['hoje'] = timezone.localdate()
    if usuario.has_perms(LEITURA_FAIR):
        resultado['cenarios'] = list(CenarioFAIR.objects.filter(ativo=ativo)
            .only('id', 'nome', 'qualidade', 'data_referencia').order_by('-data_referencia', '-pk')[:5])
    return resultado
