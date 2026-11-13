"""Perímetro explícito e revisões declaradas; nenhum atestado de segurança."""
from datetime import date, timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils import timezone
from inventario.models.base import DataHoraVersao, ModeloAuditavel


class PerimetroRelacoes(ModeloAuditavel):
    nome = models.CharField(max_length=200, unique=True, help_text="Nome exato do escopo usado nas relações; não pode ser renomeado.")
    descricao = models.TextField(validators=[MaxLengthValidator(1000)])
    ativos = models.ManyToManyField("Ativo", through="MembroPerimetro")
    criada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="perimetros_criados")
    atualizada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="perimetros_atualizados")
    atualizado_em = DataHoraVersao(auto_now=True)

    class Meta:
        ordering = ["nome"]
        default_permissions = ("view", "add", "change")

    def clean(self):
        super().clean()
        if not isinstance(self.nome, str) or not isinstance(self.descricao, str):
            raise ValidationError("Informe nome e descrição em texto.")
        self.nome, self.descricao = self.nome.strip(), self.descricao.strip()
        if not self.nome or not self.descricao:
            raise ValidationError("Nome e descrição são obrigatórios.")
        if self.pk and type(self).objects.get(pk=self.pk).nome != self.nome:
            raise ValidationError("O nome vincula relações e histórico; crie outro perímetro para outro escopo.")

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class MembroPerimetro(models.Model):
    perimetro = models.ForeignKey(PerimetroRelacoes, on_delete=models.CASCADE, related_name="membros")
    ativo = models.ForeignKey("Ativo", on_delete=models.PROTECT, related_name="perimetros_declarados")

    class Meta:
        default_permissions = ()
        constraints = [models.UniqueConstraint(fields=["perimetro", "ativo"], name="membro_perimetro_unico")]


class RevisaoCobertura(models.Model):
    RESULTADOS = [("REVISADO", "Relações vigentes revisadas"), ("SEM_RELACOES", "Nenhuma relação vigente identificada"),
                  ("LACUNAS", "Revisão com lacunas conhecidas")]
    perimetro = models.ForeignKey(PerimetroRelacoes, on_delete=models.PROTECT, related_name="revisoes")
    ativo = models.ForeignKey("Ativo", on_delete=models.PROTECT, related_name="revisoes_cobertura")
    tipo = models.CharField(max_length=12, choices=[("REDE", "Rede"), ("IDENTIDADE", "Identidade"), ("NEGOCIO", "Negócio")])
    principal = models.CharField(max_length=200, blank=True)
    resultado = models.CharField(max_length=16, choices=RESULTADOS)
    evidencia = models.TextField(validators=[MaxLengthValidator(4000)])
    observada_em = models.DateField()
    revisar_em = models.DateField()
    contexto_sha256 = models.CharField(max_length=64)
    resumo = models.JSONField()
    por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-pk"]
        default_permissions = ("view", "add")
        indexes = [models.Index(fields=["perimetro", "tipo", "principal", "ativo", "-id"], name="cobertura_ultima_idx")]
        constraints = [models.CheckConstraint(condition=models.Q(revisar_em__gt=models.F("observada_em")), name="cobertura_datas_ordenadas"),
                       models.CheckConstraint(condition=models.Q(resultado__in=["REVISADO", "SEM_RELACOES", "LACUNAS"]), name="cobertura_resultado_valido"),
                       models.CheckConstraint(condition=(models.Q(tipo="IDENTIDADE") & ~models.Q(principal="") |
                           models.Q(tipo__in=["REDE", "NEGOCIO"], principal="")), name="cobertura_principal_por_tipo")]

    def clean(self):
        super().clean()
        if not isinstance(self.evidencia, str) or not isinstance(self.principal, str):
            raise ValidationError("Evidência e principal devem ser textos.")
        self.evidencia, self.principal = self.evidencia.strip(), self.principal.strip()
        if not self.evidencia:
            raise ValidationError("Descreva a verificação e suas limitações.")
        if isinstance(self.observada_em, date) and self.observada_em > timezone.localdate():
            raise ValidationError("Observação não pode estar no futuro.")
        if isinstance(self.observada_em, date) and isinstance(self.revisar_em, date) and self.revisar_em > self.observada_em+timedelta(days=90):
            raise ValidationError("Revisões de cobertura têm validade máxima de 90 dias após a observação.")

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Revisão é histórica; registre uma nova avaliação.")
        self.full_clean()
        return super().save(*args, **kwargs)
