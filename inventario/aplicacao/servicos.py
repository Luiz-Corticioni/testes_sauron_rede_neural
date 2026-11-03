"""Entrada comum dos casos de uso e dos efeitos de uma alteração confirmada."""

from django.db import transaction, connections
from django.db.models.signals import post_delete, post_save, pre_save
from inventario.infraestrutura import auditoria
from inventario.infraestrutura.exportacao import exportar_inventario_json
from inventario.aplicacao.operacao import alterar_status, reconhecer_alerta, calcular_mttr
from inventario.aplicacao.risco import (
    invalidar_cache_risco,
    calcular_risco_banco,
    simular_correcao,
    analisar_historico_risco,
    registrar_mudanca_risco,
)
from inventario.aplicacao.cadastros import (
    salvar_cadastro,
    remover_cadastro,
    proximo_id_incidencia,
    proximo_id_vulnerabilidade,
    proximo_id_sala,
    sala_exige_autorizacao,
)


def lembrar_status(sender, instance, raw=False, **kwargs):
    if not raw:
        instance._status_anterior = (
            sender.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
        )


def registrar_transicao(sender, instance, created, raw=False, update_fields=None, **kwargs):
    from inventario.models import HistoricoIncidencia

    if raw or (update_fields is not None and "status" not in update_fields):
        return
    anterior = getattr(instance, "_status_anterior", None)
    if created or anterior != instance.status:
        HistoricoIncidencia.objects.create(
            incidencia=instance,
            incidencia_codigo=instance.pk,
            de=anterior or "",
            para=instance.status,
            por_id=auditoria.AUTOR.get(),
        )


def apos_commit(using):
    invalidar_cache_risco()
    from inventario.aplicacao.painel import invalidar_cache_painel
    invalidar_cache_painel()


def sincronizar_estado(sender, using="default", raw=False, **kwargs):
    if raw:
        return
    conexao = connections[using]
    # A fila da conexão é a fonte da verdade: rollback de savepoint remove a flag
    # junto com o callback. Uma flag booleana solta sobreviveria a esse rollback.
    if any(getattr(callback, "_sauron_invalidacao", False)
           for _, callback, _ in conexao.run_on_commit):
        return
    def invalidar():
        apos_commit(using)
    invalidar._sauron_invalidacao = True
    transaction.on_commit(invalidar, using=using)


def conectar_sinais():
    """Também cobre admin, migração e tarefas, que podem gravar models diretamente."""
    from inventario.models import Ativo, Dependencia, Incidencia, Vulnerabilidade, Sala, Alerta, CertificadoDigital

    auditoria.conectar_sinais()
    pre_save.connect(
        lembrar_status, sender=Incidencia, weak=False, dispatch_uid="sauron.risco.status_anterior"
    )
    post_save.connect(
        registrar_transicao, sender=Incidencia, weak=False, dispatch_uid="sauron.risco.historico"
    )
    for modelo in (Ativo, Vulnerabilidade, Incidencia, Dependencia, Sala, Alerta, CertificadoDigital):
        for nome, sinal in (("salvar", post_save), ("excluir", post_delete)):
            sinal.connect(
                sincronizar_estado,
                sender=modelo,
                weak=False,
                dispatch_uid=f"sauron.estado.{modelo.__name__}.{nome}",
            )
