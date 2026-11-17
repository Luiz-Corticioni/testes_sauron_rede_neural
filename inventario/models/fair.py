"""Cenário quantitativo versionado, com fontes declaradas pelo analista."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from inventario.matematica.fair import validar


class CenarioFAIR(models.Model):
    EFEITOS = [('C', 'Confidencialidade'), ('I', 'Integridade'), ('A', 'Disponibilidade'), ('OUTRO', 'Outro')]
    QUALIDADE = [('SIMULADO', 'Fictício ou demonstrativo'), ('ESTIMADO', 'Estimativa fundamentada'), ('MEDIDO', 'Observação medida')]
    nome = models.CharField(max_length=120)
    ativo = models.ForeignKey('Ativo', on_delete=models.PROTECT, related_name='cenarios_fair')
    evento = models.CharField(max_length=500)
    ameaca = models.CharField(max_length=200)
    efeito = models.CharField(max_length=5, choices=EFEITOS)
    escopo = models.CharField(max_length=300)
    origem_frequencia = models.CharField(max_length=300)
    origem_suscetibilidade = models.CharField(max_length=300, blank=True)
    origem_perdas = models.CharField(max_length=300)
    qualidade = models.CharField(max_length=10, choices=QUALIDADE)
    data_referencia = models.DateField()
    premissas = models.JSONField()
    versao_modelo = models.CharField(max_length=40, default='sauron.fair/30d-v2', editable=False)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em', '-pk']
        default_permissions = ()

    def clean(self):
        super().clean()
        for campo in ('nome', 'evento', 'ameaca', 'escopo', 'origem_frequencia', 'origem_perdas'):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor.strip():
                raise ValidationError({campo: 'Informe uma descrição ou fonte não vazia.'})
            setattr(self, campo, valor.strip())
        self.origem_suscetibilidade = (self.origem_suscetibilidade or '').strip()
        if self.data_referencia and self.data_referencia > timezone.localdate():
            raise ValidationError({'data_referencia': 'A data de referência não pode estar no futuro.'})
        try:
            self.premissas = validar(self.premissas)
        except ValueError as erro:
            raise ValidationError({'premissas': str(erro)}) from erro
        esperada = 'sauron.fair/30d-v2' if 'slef' in self.premissas else 'sauron.fair/30d-v1'
        if self.versao_modelo != esperada:
            raise ValidationError({'premissas': 'Versão do modelo incompatível com as premissas registradas.'})
        if self.premissas['modo'] != 'LEF' and not self.origem_suscetibilidade.strip():
            raise ValidationError({'origem_suscetibilidade': 'Informe a origem da suscetibilidade ou da capacidade e resistência.'})
        if self.ativo_id and self.ativo.status in ('INATIVO', 'BAIXADO'):
            raise ValidationError({'ativo': 'Selecione um ativo ativo ou em manutenção.'})


class ExecucaoFAIR(models.Model):
    cenario = models.ForeignKey(CenarioFAIR, on_delete=models.PROTECT, related_name='execucoes')
    versao_modelo = models.CharField(max_length=40)
    n = models.PositiveIntegerField()
    seed = models.BigIntegerField()
    premissas_snapshot = models.JSONField()
    resultado = models.JSONField()
    versao_python = models.CharField(max_length=40)
    versao_numpy = models.CharField(max_length=40)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em', '-pk']
        default_permissions = ()
