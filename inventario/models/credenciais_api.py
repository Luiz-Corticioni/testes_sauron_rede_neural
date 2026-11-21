"""Credenciais de integração; nunca persistem o segredo apresentado ao cliente."""
import uuid

from django.conf import settings
from django.db import models


class CredencialAPI(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dono = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    segredo_hash = models.CharField(max_length=64, unique=True)
    escopos = models.JSONField(default=list)
    criada_em = models.DateTimeField(auto_now_add=True)
    expira_em = models.DateTimeField()
    revogada_em = models.DateTimeField(null=True, blank=True)
    janela_em = models.DateTimeField(null=True, blank=True)
    requisicoes_janela = models.PositiveIntegerField(default=0)


class LimiteOrigemAPI(models.Model):
    chave = models.CharField(max_length=64, primary_key=True)
    expira_em = models.DateTimeField(db_index=True)
    quantidade = models.PositiveIntegerField(default=0)
