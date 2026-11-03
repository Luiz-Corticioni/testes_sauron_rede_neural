from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction

from inventario.models.base import ModeloAuditavel
from inventario.models.conversoes import ConversaoDependencia


class Dependencia(ConversaoDependencia, ModeloAuditavel):
    dependente = models.ForeignKey("Ativo", on_delete=models.CASCADE, related_name="dependencias")
    fornecedor = models.ForeignKey("Ativo", on_delete=models.CASCADE, related_name="dependentes")
    peso = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(0.999999)])
    descricao = models.CharField(max_length=200, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["dependente", "fornecedor"], name="dependencia_unica"),
            models.CheckConstraint(
                condition=~models.Q(dependente=models.F("fornecedor")), name="sem_autodependencia"
            ),
        ]

    def clean(self):
        super().clean()
        from inventario.aplicacao.validacao_dependencias import validar_dependencia

        validar_dependencia(self)

    def save(self, *args, **kwargs):
        from inventario.infraestrutura.auditoria import travar_escrita

        using = kwargs.get("using", "default")
        with transaction.atomic(using=using):
            travar_escrita(using)
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.dependente_id} ← {self.peso:.2f} — {self.fornecedor_id}"
