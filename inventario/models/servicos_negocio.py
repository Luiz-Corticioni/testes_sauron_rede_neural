"""Serviços declarados associados aos perímetros já existentes."""
from django.conf import settings
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from django.db import models
from inventario.models.base import DataHoraVersao, ModeloAuditavel


class ServicoNegocio(ModeloAuditavel):
    nome = models.CharField(max_length=160, unique=True)
    descricao = models.TextField(validators=[MaxLengthValidator(1000)])
    responsavel = models.CharField(max_length=160)
    impacto_interrupcao = models.TextField(validators=[MaxLengthValidator(1000)])
    criticidade = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(4)])
    objetivo_recuperacao_horas = models.PositiveIntegerField(null=True, blank=True,
        help_text='Objetivo declarado de recuperação em horas; não é garantia nem teste realizado.')
    perimetro = models.ForeignKey('PerimetroRelacoes', on_delete=models.PROTECT, related_name='servicos_negocio')
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = DataHoraVersao(auto_now=True)

    class Meta:
        ordering = ['nome', 'pk']
        default_permissions = ('view', 'add', 'change')

    def __str__(self):
        return self.nome
