"""Sensores declarados e eventos minimizados importados manualmente."""
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.conf import settings
from inventario.models.base import ModeloAuditavel


class SensorHoneypot(ModeloAuditavel):
    nome = models.CharField(max_length=100, unique=True)
    localizacao = models.CharField(max_length=150, blank=True)
    responsavel = models.CharField(max_length=120)
    ativo = models.ForeignKey("Ativo", null=True, blank=True, on_delete=models.PROTECT)
    ambiente = models.CharField(max_length=15, choices=[("DEMONSTRACAO", "Demonstração"), ("OPERACIONAL", "Operacional")], default="DEMONSTRACAO")
    habilitado = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nome", "pk"]

    def __str__(self):
        return self.nome


class EventoHoneypot(models.Model):
    TIPOS = [(v, v) for v in ("CONEXAO", "LOGIN_FALHOU", "LOGIN_ACEITO", "OUTRO")]
    sensor = models.ForeignKey(SensorHoneypot, on_delete=models.PROTECT, related_name="eventos")
    identificador = models.CharField(max_length=100, validators=[RegexValidator(r"^[A-Za-z0-9_.:-]+$")])
    observado_em = models.DateTimeField()
    recebido_em = models.DateTimeField(auto_now_add=True)
    origem_ip = models.GenericIPAddressField(null=True, blank=True)
    tipo = models.CharField(max_length=20, choices=TIPOS)

    class Meta:
        ordering = ["-observado_em", "-pk"]
        constraints = [models.UniqueConstraint(fields=["sensor", "identificador"], name="honeypot_evento_unico")]


class RevisaoEventoHoneypot(models.Model):
    CLASSIFICACOES = [("TESTE", "Teste autorizado"), ("SUSPEITO", "Suspeito"), ("INCONCLUSIVO", "Inconclusivo")]
    OBSERVACOES = [("EXERCICIO", "Exercício autorizado informado"), ("ANALISAR", "Requer análise adicional"),
                   ("SEM_CONTEXTO", "Contexto insuficiente")]
    evento = models.ForeignKey(EventoHoneypot, on_delete=models.PROTECT, related_name="revisoes")
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    classificacao = models.CharField(max_length=15, choices=CLASSIFICACOES)
    observacao = models.CharField(max_length=15, choices=OBSERVACOES)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em", "-pk"]


class PoliticaRetencaoHoneypot(models.Model):
    dias = models.PositiveSmallIntegerField(default=90, validators=[MinValueValidator(30), MaxValueValidator(180)])
    atualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        default_permissions = ("view", "change")
        constraints = [models.CheckConstraint(condition=models.Q(pk=1), name="politica_honeypot_unica"),
                       models.CheckConstraint(condition=models.Q(dias__gte=30, dias__lte=180), name="politica_honeypot_prazo")]
