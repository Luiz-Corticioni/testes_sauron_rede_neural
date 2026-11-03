from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from inventario.dominio.enums import classificar_cvss

from inventario.models.base import ModeloAuditavel
from inventario.models.conversoes import ConversaoVulnerabilidade


class Vulnerabilidade(ConversaoVulnerabilidade, ModeloAuditavel):
    CATEGORIAS = [
        ("RCE", "Execução remota de código"),
        ("AUTH", "Autenticação"),
        ("DOS", "Negação de serviço"),
        ("INFO", "Exposição de informação"),
        ("PRIV", "Escalação de privilégio"),
        ("INJ", "Injeção"),
        ("CFG", "Configuração insegura"),
        ("OUTRA", "Outra"),
    ]
    id = models.CharField(primary_key=True, max_length=30)
    cve_id = models.CharField(max_length=30, null=True, blank=True, unique=True)
    descricao = models.TextField()
    categoria = models.CharField(max_length=10, choices=CATEGORIAS, default="OUTRA")
    cvss = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(10)])
    faixas_afetadas = models.JSONField(default=list, blank=True)
    vex = models.JSONField(default=list, blank=True)
    cvss_v4 = models.JSONField(default=dict, blank=True)
    confianca_nvd = models.CharField(max_length=10, blank=True)
    cvss_versao = models.CharField(max_length=10, default="3.1")
    cvss_vetor = models.CharField(max_length=255, blank=True)
    fonte = models.CharField(max_length=40, default="Manual")
    publicada_em = models.DateField(null=True, blank=True)
    referencias = models.JSONField(default=list, blank=True)
    epss = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(1)])
    epss_data = models.DateField(null=True, blank=True)
    epss_observacao = models.ForeignKey("ObservacaoEPSS", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    kev = models.BooleanField(default=False)
    kev_adicionada_em = models.DateField(null=True, blank=True)
    kev_prazo = models.DateField(null=True, blank=True)
    uso_ransomware = models.CharField(max_length=20, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-cvss", "id"]
        indexes = [models.Index(fields=["kev"], name="vul_kev_idx")]

    @property
    def severidade(self):
        return classificar_cvss(self.cvss).value

    def clean(self):
        super().clean()
        import math
        from django.core.exceptions import ValidationError
        if (type(self.cvss) not in (int, float) or not math.isfinite(self.cvss)
                or not 0 <= self.cvss <= 10 or abs(self.cvss*10-round(self.cvss*10)) > 1e-8):
            raise ValidationError({"cvss": "CVSS deve ser nota finita de 0 a 10, com uma casa decimal."})
        if not isinstance(self.faixas_afetadas, list) or not isinstance(self.vex, list):
            raise ValidationError("Faixas/VEX devem ser listas JSON.")
        from inventario.dominio.matching import identidade
        try:
            for item in self.faixas_afetadas:
                identidade(item["criteria"])
            for item in self.vex:
                identidade(item["cpe23"])
                if item.get("status") != "not_affected" or not item.get("justificativa", "").strip():
                    raise ValueError("VEX exige status not_affected e justificativa.")
        except (ValueError, TypeError, KeyError) as erro:
            raise ValidationError(str(erro)) from erro
        if self.epss_observacao_id:
            from inventario.models.epss import ObservacaoEPSS
            observacao = ObservacaoEPSS.objects.filter(pk=self.epss_observacao_id).values("cve_id", "epss", "data").first()
            if observacao is None or (observacao["cve_id"], observacao["epss"], observacao["data"]) != (self.cve_id, self.epss, self.epss_data):
                raise ValidationError("EPSS e origem não correspondem à CVE, valor e data registrados.")
        if self.epss is not None and not math.isfinite(self.epss):
            raise ValidationError({"epss": "EPSS deve ser número finito entre 0 e 1."})

    def save(self, *args, **kwargs):
        self.id = self.id.upper()
        if self.cve_id:
            self.cve_id = self.cve_id.upper()
        campos = kwargs.get("update_fields")
        if campos is None or "cve_id" in campos:
            anterior = type(self).objects.filter(pk=self.pk).values("cve_id").first()
            if anterior and anterior["cve_id"] != self.cve_id:
                self.epss = self.epss_data = self.epss_observacao = None
                if campos is not None:
                    kwargs["update_fields"] = set(campos) | {"epss", "epss_data", "epss_observacao"}
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cve_id or self.id} — CVSS {self.cvss:.1f}"
