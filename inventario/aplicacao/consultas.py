"""Identidade única usada pelas consultas do terminal e da interface web."""

from django.db.models import Q
from inventario.models import Ativo


def consultar_ativo(termo):
    termo = str(termo).strip()
    if termo.isascii() and termo.isdigit():
        numero = int(termo)
        if not 1 <= numero <= 2**63 - 1:
            raise Ativo.DoesNotExist
        return Ativo.objects.select_related("sala").get(id_numerico=numero)
    try:
        return Ativo.objects.select_related("sala").get(
            Q(pk__iexact=termo) | Q(hostname__iexact=termo) | Q(nome__iexact=termo)
        )
    except Ativo.MultipleObjectsReturned as erro:
        raise ValueError("Há nomes repetidos. Consulte pelo ID numérico, código ou hostname.") from erro
