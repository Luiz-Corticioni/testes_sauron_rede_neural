from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from inventario.models.base import ModeloAuditavel


class Incidente(ModeloAuditavel):
    ativo = models.ForeignKey("Ativo", on_delete=models.PROTECT, related_name="incidentes")
    titulo = models.CharField(max_length=160)
    descricao = models.TextField()
    gravidade = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    aberto_em = models.DateTimeField(default=timezone.now)
    encerrado_em = models.DateTimeField(null=True, blank=True)


class CertificadoDigital(ModeloAuditavel):
    ativo = models.ForeignKey("Ativo", on_delete=models.CASCADE, related_name="certificados")
    dominio = models.CharField(max_length=255)
    emissor = models.CharField(max_length=160, blank=True)
    expira_em = models.DateField()


class Software(ModeloAuditavel):
    """Inventário mínimo de componentes; não é uma SBOM SPDX/CycloneDX completa."""

    ativo = models.ForeignKey("Ativo", on_delete=models.CASCADE, related_name="softwares")
    nome = models.CharField(max_length=120)
    versao = models.CharField(max_length=80)
    fornecedor = models.CharField(max_length=120)
    purl = models.CharField(max_length=512, blank=True, help_text="Package URL exata, incluindo versão; opcional no cadastro manual.")
    cpe23 = models.CharField(
        max_length=512,
        blank=True,
        help_text="CPE 2.3 com fabricante, produto e versão definidos; opcional.",
    )

    class Meta:
        ordering = ["ativo_id", "nome", "versao"]
        constraints = [
            models.UniqueConstraint(
                fields=["ativo", "nome", "versao"], condition=models.Q(purl=""), name="software_unico_por_ativo"
            ),
            models.UniqueConstraint(fields=["ativo", "purl"], condition=~models.Q(purl=""), name="software_purl_por_ativo"),
        ]

    def clean(self):
        super().clean()
        from inventario.dominio.classificacao import validar_cpe

        if self.purl:
            from inventario.dominio.documentos import purl_exata
            try:
                self.purl = purl_exata(self.purl, self.versao)
            except ValueError as erro:
                raise ValidationError({"purl": str(erro)}) from erro
        if self.pk:
            anterior = type(self).objects.filter(pk=self.pk).values("ativo_id", "purl", "versao").first()
            mudou = anterior and any(anterior[k] != getattr(self, k) for k in anterior)
            if mudou and (self.itens_sbom.exists() or self.achados_componentes.exists() or self.incidencia_set.exists()):
                raise ValidationError("Identidade de componente com evidências não pode mudar; cadastre nova versão.")
        if self.cpe23:
            try:
                validar_cpe(self.cpe23)
            except ValueError as erro:
                raise ValidationError({"cpe23": str(erro)}) from erro

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class Alerta(ModeloAuditavel):
    TIPOS = [
        (t, t)
        for t in ("LOGIN", "EOL", "CERT", "SLA", "KEV", "TENDENCIA", "IMUNE", "SEM_DONO", "ACEITE_VENCIDO")
    ]
    tipo = models.CharField(max_length=20, choices=TIPOS)
    severidade = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    ativo = models.ForeignKey(
        "Ativo", null=True, blank=True, on_delete=models.PROTECT, related_name="alertas"
    )
    mensagem = models.TextField()
    chave = models.CharField(max_length=160)
    criado_em = models.DateTimeField(default=timezone.now)
    reconhecido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT
    )
    reconhecido_em = models.DateTimeField(null=True, blank=True)
    suprimido_ate = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-severidade", "-criado_em", "id"]
        permissions = [("reconhecer_alerta", "Pode reconhecer alertas")]
        constraints = [
            models.UniqueConstraint(
                fields=["tipo", "ativo", "chave"],
                condition=models.Q(reconhecido_em__isnull=True, ativo__isnull=False),
                name="alerta_ativo_pendente_unico",
            ),
            # SQLite trata NULLs como distintos: a regra global precisa de índice próprio.
            models.UniqueConstraint(
                fields=["tipo", "chave"],
                condition=models.Q(reconhecido_em__isnull=True, ativo__isnull=True),
                name="alerta_global_pendente_unico",
            ),
        ]

