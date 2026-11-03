"""Estado efêmero de autenticação compartilhado pelo banco de dados."""
from django.db import models


class LimiteLogin(models.Model):
    chave = models.CharField(max_length=80, primary_key=True)
    quantidade = models.PositiveIntegerField(default=0)
    usuarios = models.JSONField(default=list)
    expira_em = models.DateTimeField(db_index=True)

    class Meta:
        default_permissions = ()
