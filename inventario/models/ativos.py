from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from inventario.dominio.enums import TipoEquipamento
from inventario.dominio.equipamentos import gerar_hostname, gerar_id_ativo, validar_id_ativo

from inventario.models.base import ModeloAuditavel

TIPOS = [(item.value, item.rotulo) for item in TipoEquipamento]
from inventario.models.conversoes import ConversaoAtivo


class Ativo(ConversaoAtivo, ModeloAuditavel):
    class Status(models.TextChoices):
        ATIVO = "ATIVO", "Ativo"
        MANUTENCAO = "MANUTENCAO", "Em manutenção"
        INATIVO = "INATIVO", "Inativo"
        BAIXADO = "BAIXADO", "Baixado"

    id = models.CharField(primary_key=True, max_length=7, editable=False)
    id_numerico = models.PositiveBigIntegerField(unique=True, editable=False, blank=True)
    tipo = models.CharField(max_length=1, choices=TIPOS)
    nome = models.CharField(max_length=100)
    hostname = models.CharField(max_length=80, unique=True, blank=True)
    fabricante = models.CharField(max_length=80)
    modelo = models.CharField(max_length=100, blank=True)
    ip = models.GenericIPAddressField(protocol="IPv4", null=True, blank=True, unique=True)
    sistema_operacional = models.CharField(max_length=120, blank=True)
    versao = models.CharField(max_length=80, blank=True)
    responsavel = models.CharField(max_length=120, blank=True)
    contato = models.EmailField(blank=True)
    confidencialidade = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    integridade = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    disponibilidade = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    exposto_internet = models.BooleanField(default=False)
    linha_base_saudavel = models.BooleanField(default=False)
    evidencia_scan = models.TextField(blank=True)
    zona_rede = models.CharField(max_length=80, blank=True)
    portas_servicos = models.JSONField(default=list, blank=True)
    sala = models.ForeignKey("Sala", on_delete=models.PROTECT, related_name="ativos")
    criticidade = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ATIVO)
    fim_suporte = models.DateField(null=True, blank=True)
    atributos = models.JSONField(default=dict, blank=True)
    alocacao_excepcional_autorizada = models.BooleanField(default=False)
    justificativa_excecao = models.TextField(blank=True)
    autorizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="alocacoes_autorizadas",
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    vulnerabilidades = models.ManyToManyField(
        "Vulnerabilidade", through="Incidencia", related_name="ativos"
    )

    class Meta:
        ordering = ["id"]
        permissions = [("autorizar_alocacao_excepcional", "Pode autorizar alocação excepcional"),
                       ("declarar_linha_base_saudavel", "Pode declarar linha de base saudável")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["ATIVO", "MANUTENCAO", "INATIVO", "BAIXADO"]),
                name="ativo_status_valido",
            )
        ]

    def clean(self):
        super().clean()
        from inventario.infraestrutura.identidades import validar_numero

        validar_numero(self.id_numerico)
        anterior = Ativo.objects.filter(pk=self.pk).first() if self.pk else None
        if self.linha_base_saudavel and not self.evidencia_scan.strip():
            raise ValidationError({"evidencia_scan": "Informe a evidência/ID do scan."})
        if self.linha_base_saudavel or (anterior and anterior.linha_base_saudavel):
            from django.contrib.auth import get_user_model
            from inventario.infraestrutura.auditoria import AUTOR
            autor = get_user_model().objects.filter(pk=AUTOR.get()).first()
            if not autor or not autor.has_perm("inventario.declarar_linha_base_saudavel"):
                raise ValidationError("Declaração/edição da linha de base exige permissão específica.")
        if self.alocacao_excepcional_autorizada and (
                anterior is None or any(getattr(self,c)!=getattr(anterior,c) for c in
                ("sala_id","alocacao_excepcional_autorizada","justificativa_excecao","autorizado_por_id"))):
            from django.contrib.auth import get_user_model
            from inventario.infraestrutura.auditoria import AUTOR
            autor=get_user_model().objects.filter(pk=AUTOR.get()).first()
            if not autor or not autor.has_perm("inventario.autorizar_alocacao_excepcional") or self.autorizado_por_id!=autor.pk:
                raise ValidationError("Autorização de alocação exige autor corrente com permissão.")
        if not isinstance(self.atributos, dict):
            raise ValidationError({"atributos": "Use um objeto JSON, por exemplo {}."})
        import re

        if self.hostname and not re.fullmatch(
            r"[A-Za-z](?:[A-Za-z0-9-]{0,78}[A-Za-z0-9])?", self.hostname
        ):
            raise ValidationError(
                {"hostname": "Comece com letra; use letras, números e hífen, sem espaços."}
            )
        from inventario.dominio.classificacao import validar_portas

        try:
            validar_portas(self.portas_servicos)
        except ValueError as erro:
            raise ValidationError({"portas_servicos": str(erro)}) from erro
        if self.id:
            try:
                validar_id_ativo(self.id, self.tipo)
            except ValueError as erro:
                raise ValidationError({"id": str(erro)}) from erro
        if self.sala_id and (
            self.sala.restrita
            or (self.sala.tipos_permitidos and self.tipo not in self.sala.tipos_permitidos)
        ):
            if not self.alocacao_excepcional_autorizada:
                raise ValidationError(
                    {"sala": "Este tipo de ativo não é permitido na sala sem autorização especial."}
                )
            if self.autorizado_por_id and not self.autorizado_por.has_perm("inventario.autorizar_alocacao_excepcional"):
                raise ValidationError("Autorizador não possui permissão para exceção.")
            if not self.autorizado_por_id or not self.justificativa_excecao.strip():
                raise ValidationError("A exceção exige autorizador e justificativa.")

    def save(self, *args, **kwargs):
        from inventario.infraestrutura.auditoria import travar_escrita
        from inventario.infraestrutura.identidades import reservar_numero, validar_numero

        using = kwargs.get("using") or self._state.db or "default"
        with transaction.atomic(using=using):
            travar_escrita(using)
            validar_numero(self.id_numerico)
            anterior = Ativo.objects.using(using).filter(pk=self.pk).values("id_numerico").first()
            if anterior:
                if self.id_numerico not in (None, anterior["id_numerico"]):
                    raise ValidationError({"id_numerico": "O ID numérico não pode ser alterado."})
                self.id_numerico = anterior["id_numerico"]
            else:
                self.id_numerico = reservar_numero(self.id_numerico, using)
            if not self.id:
                sequencia = Ativo.objects.filter(tipo=self.tipo).count() + 1
                candidato = gerar_id_ativo(self.tipo, self.fabricante, sequencia)
                while Ativo.objects.filter(pk=candidato).exists():
                    sequencia += 1
                    candidato = gerar_id_ativo(self.tipo, self.fabricante, sequencia)
                self.id = candidato
            if not self.hostname:
                sequencia = int(self.id[-5:])
                self.hostname = gerar_hostname(self.tipo, self.fabricante, sequencia)
            self.full_clean()
            super().save(*args, **kwargs)
            if not self.linha_base_saudavel:
                from inventario.models import Anticorpo
                from inventario.aplicacao.imune_padroes import base_correspondente
                for m in Anticorpo.objects.filter(estado="DESCARTADO", descartado_por_ativo=self):
                    outra = base_correspondente(m, list(Ativo.objects.filter(linha_base_saudavel=True)), m.vulnerabilidade)
                    m.descartado_por_ativo = outra
                    m.estado = "DESCARTADO" if outra else "ATIVO"
                    m.save(update_fields=["estado", "descartado_por_ativo"])

    def __str__(self):
        return f"{self.hostname} ({self.id})"
