"""Atualiza o estado Django; o tipo das colunas no banco não muda."""

import inventario.models.base
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0027_versaoinventario_limitelogin_geracao'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterField(
                    model_name='perimetrorelacoes',
                    name='atualizado_em',
                    field=inventario.models.base.DataHoraVersao(auto_now=True),
                ),
                migrations.AlterField(
                    model_name='relacaoativos',
                    name='atualizado_em',
                    field=inventario.models.base.DataHoraVersao(auto_now=True),
                ),
            ],
        ),
    ]
