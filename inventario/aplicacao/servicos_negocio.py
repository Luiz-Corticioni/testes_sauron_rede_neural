"""Cadastro auditado e proteção de edição concorrente dos serviços."""
from django.core.exceptions import ValidationError
from django.db import transaction
from inventario.aplicacao.autorizacao import exigir
from inventario.aplicacao.cobertura import LEITURA
from inventario.infraestrutura.auditoria import travar_escrita, usar_usuario
from inventario.models import ServicoNegocio

CAMPOS = ('nome', 'descricao', 'responsavel', 'impacto_interrupcao', 'criticidade',
          'objetivo_recuperacao_horas', 'perimetro')


def salvar_servico(usuario, dados, pk=None, versao=''):
    with transaction.atomic():
        travar_escrita()
        exigir(usuario, *LEITURA, 'inventario.view_serviconegocio',
               f"inventario.{'change' if pk else 'add'}_serviconegocio")
        with usar_usuario(usuario):
            servico = ServicoNegocio.objects.get(pk=pk) if pk else ServicoNegocio(criado_por=usuario)
            if pk and servico.atualizado_em.isoformat() != versao:
                raise ValidationError('O serviço mudou; recarregue antes de editar.')
            for campo in CAMPOS:
                setattr(servico, campo, dados[campo])
            servico.full_clean()
            servico.save()
            return servico
