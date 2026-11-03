from django.core.exceptions import ValidationError
from django.db import models, transaction
from inventario.dominio.enums import TipoEquipamento

from inventario.models.base import ModeloAuditavel

TIPOS = [(item.value, item.rotulo) for item in TipoEquipamento]


class Sala(ModeloAuditavel):
    id = models.CharField(primary_key=True, max_length=30, help_text="Ex.: SALA-TI-001")
    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=30, default="TI")
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="subsetores"
    )
    tipos_permitidos = models.JSONField(default=list, blank=True)
    restrita = models.BooleanField(default=False)

    class Meta:
        ordering = ["id"]

    def clean(self):
        super().clean()
        validos = {codigo for codigo, _ in TIPOS}
        if not isinstance(self.tipos_permitidos, list) or any(
            not isinstance(tipo, str) or tipo not in validos for tipo in self.tipos_permitidos
        ):
            raise ValidationError({"tipos_permitidos": "Use lista de códigos de 1 a 9."})
        if Sala.objects.filter(pk=self.pk).exists():
            for ativo in self.ativos.exclude(status="BAIXADO"):
                incompatível = bool(
                    self.tipos_permitidos and ativo.tipo not in self.tipos_permitidos
                )
                if (self.restrita or incompatível) and not ativo.alocacao_excepcional_autorizada:
                    raise ValidationError(
                        "Mova ou autorize excepcionalmente os ativos existentes "
                        "antes de restringir esta sala."
                    )
        vistos = {self.pk}
        pai = self.parent if self.parent_id else None
        while pai is not None:
            if pai.pk in vistos:
                raise ValidationError({"parent": "A hierarquia de salas não pode ter ciclos."})
            vistos.add(pai.pk)
            pai = pai.parent

    def save(self, *args, **kwargs):
        from inventario.infraestrutura.auditoria import travar_escrita

        with transaction.atomic():
            travar_escrita()
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.id} — {self.nome}"
