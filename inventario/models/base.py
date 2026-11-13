from datetime import timedelta
from django.db import DEFAULT_DB_ALIAS, models, transaction


class DataHoraVersao(models.DateTimeField):
    """Versão temporal estritamente crescente por registro sob a trava de escrita."""

    def pre_save(self, instancia, add):
        instante = super().pre_save(instancia, add)
        if not add and instancia.pk is not None:
            usando = instancia._state.db or DEFAULT_DB_ALIAS
            anterior = (type(instancia)._base_manager.using(usando).filter(pk=instancia.pk)
                        .values_list(self.attname, flat=True).first())
            if anterior is not None and instante <= anterior:
                instante = anterior + timedelta(microseconds=1)
                setattr(instancia, self.attname, instante)
        return instante


class ModeloAuditavel(models.Model):
    """Mantém a alteração e seu registro de auditoria na mesma transação."""

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        from inventario.infraestrutura.auditoria import travar_escrita

        campos = kwargs.get("update_fields")
        if campos is not None and not campos:
            return None
        if campos is not None and hasattr(self, "atualizado_em"):
            kwargs["update_fields"] = set(campos) | {"atualizado_em"}
        with transaction.atomic(using=kwargs.get("using", "default")):
            travar_escrita(kwargs.get("using", "default"))
            return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        with transaction.atomic(using=kwargs.get("using", "default")):
            return super().delete(*args, **kwargs)


class TravaDominio(models.Model):
    """Linha técnica usada para serializar escritores antes de validar o grafo."""

    versao = models.PositiveIntegerField(default=0)


class ContadorAtivo(models.Model):
    """Sequência persistida: excluir um ativo não torna seu número reutilizável."""

    ultimo = models.PositiveBigIntegerField(default=0)


class VersaoInventario(models.Model):
    """Geração transacional para invalidar cálculos entre processos."""

    versao = models.PositiveBigIntegerField(default=0)
