"""Commit-check de uma aresta candidata; o save bloqueia escritores antes da leitura."""

from scipy import sparse
from django.core.exceptions import ValidationError
from django.conf import settings

from inventario.matematica.estabilidade import validar_matriz
from inventario.models import Ativo, Dependencia


def validar_dependencia(candidata):
    if settings.RISCO_POLITICA == "noisy-or":
        return # Política experimental: validações escalares/diagonal permanecem no model.
    if not candidata.dependente_id or not candidata.fornecedor_id:
        return
    ids = list(Ativo.objects.order_by("id").values_list("id", flat=True))
    indices = {identificador: i for i, identificador in enumerate(ids)}
    matriz = sparse.lil_matrix((len(ids), len(ids)))
    existentes = Dependencia.objects.exclude(pk=candidata.pk)
    for dependente, fornecedor, peso in existentes.values_list(
        "dependente_id", "fornecedor_id", "peso"
    ):
        matriz[indices[dependente], indices[fornecedor]] = peso
    try:
        matriz[indices[candidata.dependente_id], indices[candidata.fornecedor_id]] = candidata.peso
        validar_matriz(matriz)
    except (ValueError, KeyError) as erro:
        raise ValidationError({"peso": str(erro)}) from erro
