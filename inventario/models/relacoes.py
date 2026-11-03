"""Evidências direcionadas entre ativos; não são permissões do próprio Sauron."""
from django.conf import settings
from datetime import date
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models, transaction
from django.utils import timezone
from inventario.models.base import ModeloAuditavel


class RelacaoAtivos(ModeloAuditavel):
    TIPOS = [("REDE", "Tráfego permitido"), ("IDENTIDADE", "Acesso por identidade"),
             ("NEGOCIO", "Dependência de negócio")]
    PROTOCOLOS = [("tcp", "TCP"), ("udp", "UDP"), ("icmp", "ICMP")]
    PRIVILEGIOS = [("LEITURA", "Leitura"), ("EXECUCAO", "Execução"), ("ADMIN", "Administração")]
    origem = models.ForeignKey("Ativo", on_delete=models.PROTECT, related_name="relacoes_saida")
    destino = models.ForeignKey("Ativo", on_delete=models.PROTECT, related_name="relacoes_entrada")
    tipo = models.CharField(max_length=12, choices=TIPOS)
    escopo = models.CharField(max_length=200, help_text="Aplicação, ambiente ou domínio exato da relação.")
    protocolo = models.CharField(max_length=4, choices=PROTOCOLOS, blank=True)
    porta = models.PositiveIntegerField(default=0, help_text="Porta do destino; use 0 para ICMP ou outra camada.")
    principal = models.CharField(max_length=200, blank=True, help_text="Identificador da conta/serviço externo, sem senhas ou tokens.")
    privilegio = models.CharField(max_length=12, choices=PRIVILEGIOS, blank=True)
    fonte = models.CharField(max_length=200)
    evidencia = models.TextField(validators=[MaxLengthValidator(4000)])
    observada_em = models.DateField()
    revisar_em = models.DateField(help_text="No início desta data a relação sai da análise até ser revisada.")
    vigente = models.BooleanField(default=True, help_text="Desmarque para revogar preservando o registro.")
    criada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="relacoes_criadas")
    atualizada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="relacoes_atualizadas")
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tipo", "escopo", "pk"]
        default_permissions = ("view", "add", "change")
        indexes = [models.Index(fields=["tipo", "escopo", "principal", "id"], name="relacoes_camadas_idx")]
        constraints = [
            models.CheckConstraint(condition=~models.Q(origem=models.F("destino")), name="relacao_sem_autolaco"),
            models.CheckConstraint(condition=models.Q(revisar_em__gt=models.F("observada_em")), name="relacao_datas_ordenadas"),
            models.CheckConstraint(condition=(
                models.Q(tipo="REDE", principal="", privilegio="") & (
                    models.Q(protocolo__in=["tcp", "udp"], porta__gte=1, porta__lte=65535) |
                    models.Q(protocolo="icmp", porta=0)) |
                models.Q(tipo="IDENTIDADE", protocolo="", porta=0, privilegio__in=["LEITURA", "EXECUCAO", "ADMIN"]) & ~models.Q(principal="") |
                models.Q(tipo="NEGOCIO", protocolo="", porta=0, principal="", privilegio="")
            ), name="relacao_campos_por_tipo"),
            models.UniqueConstraint(fields=["origem", "destino", "tipo", "escopo", "protocolo", "porta", "principal", "privilegio"], name="relacao_identidade_unica"),
        ]

    def clean(self):
        super().clean()
        for campo in ("escopo", "fonte", "evidencia", "principal"):
            valor = getattr(self, campo)
            if isinstance(valor, str):
                setattr(self, campo, valor.strip())
        if not self.escopo or not self.fonte or not self.evidencia:
            raise ValidationError("Escopo, fonte e evidência são obrigatórios.")
        if isinstance(self.observada_em, date) and self.observada_em > timezone.localdate():
            raise ValidationError("A observação não pode estar no futuro.")
        if self.tipo == "IDENTIDADE" and not self.principal:
            raise ValidationError("Informe a identidade externa; nunca informe credenciais.")

    def save(self, *args, **kwargs):
        from inventario.infraestrutura.auditoria import travar_escrita
        using = kwargs.get("using", "default")
        with transaction.atomic(using=using):
            travar_escrita(using)
            self.full_clean()
            return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.origem_id} → {self.destino_id} · {self.get_tipo_display()} · {self.escopo}"
