"""Reserva de identidade numérica sob a mesma trava usada para gravar o ativo."""

from django.core.exceptions import ValidationError


def validar_numero(numero):
    if numero is not None and (type(numero) is not int or not 1 <= numero <= 2**63 - 1):
        raise ValidationError({"id_numerico": "O ID numérico deve ser um inteiro positivo."})


def reservar_numero(numero=None, using="default"):
    """Chamado dentro de transaction.atomic, depois de travar_escrita.

    Uma restauração JSON pode preservar um número explícito. A unicidade continua
    imposta pelo banco; a sequência avança para não colidir com a próxima geração.
    """
    from inventario.models import ContadorAtivo

    validar_numero(numero)
    contador, _ = ContadorAtivo.objects.using(using).get_or_create(pk=1)
    escolhido = contador.ultimo + 1 if numero is None else numero
    validar_numero(escolhido)
    if escolhido > contador.ultimo:
        ContadorAtivo.objects.using(using).filter(pk=1).update(ultimo=escolhido)
    return escolhido
