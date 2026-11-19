"""Visão de negócio sobre perímetros existentes, sem deduzir impacto real."""
from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods
from inventario.aplicacao.servicos_negocio import salvar_servico
from inventario.models import Incidencia, ServicoNegocio


class ServicoForm(forms.ModelForm):
    versao = forms.CharField(required=False, widget=forms.HiddenInput)
    class Meta:
        model = ServicoNegocio
        fields = ('nome', 'descricao', 'responsavel', 'impacto_interrupcao', 'criticidade',
                  'objetivo_recuperacao_horas', 'perimetro')
        labels = {'impacto_interrupcao': 'Impacto declarado de uma interrupção',
                  'objetivo_recuperacao_horas': 'Objetivo de recuperação em horas',
                  'perimetro': 'Perímetro de ativos que sustenta o serviço'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial['versao'] = self.instance.atualizado_em.isoformat()


@require_GET
def lista(request):
    servicos = ServicoNegocio.objects.select_related('perimetro').annotate(
        total_ativos=Count('perimetro__membros', distinct=True)).order_by('nome', 'pk')[:100]
    return render(request, 'inventario/servicos_negocio.html', {'servicos': servicos})


@require_http_methods(['GET', 'POST'])
def formulario(request, pk=None):
    instance = get_object_or_404(ServicoNegocio, pk=pk) if pk else ServicoNegocio()
    form = ServicoForm(request.POST or None, instance=instance)
    if request.method == 'POST' and form.is_valid():
        try:
            servico = salvar_servico(request.user, form.cleaned_data, pk, form.cleaned_data['versao'])
        except IntegrityError:
            form.add_error('nome', 'Já existe um serviço com este nome.')
        except ValidationError as erro:
            form.add_error(None, '; '.join(erro.messages))
        else:
            messages.success(request, 'Serviço salvo. Confira o perímetro e suas evidências.')
            return redirect('servico_negocio', pk=servico.pk)
    return render(request, 'inventario/formulario.html', {'form': form, 'titulo': 'Editar serviço de negócio' if pk else 'Declarar serviço de negócio',
        'cancelar_url': reverse('servicos_negocio')})


@require_GET
def detalhe(request, pk):
    servico = get_object_or_404(ServicoNegocio.objects.select_related('perimetro', 'criado_por'), pk=pk)
    membros = servico.perimetro.membros.select_related('ativo').order_by('ativo_id')[:100]
    contexto = {'servico': servico, 'membros': membros}
    if request.user.has_perms(('inventario.view_incidencia', 'inventario.view_vulnerabilidade')):
        contexto['incidencias'] = Incidencia.objects.filter(
            ativo_id__in=servico.perimetro.membros.values('ativo_id')).select_related(
                'ativo', 'vulnerabilidade').order_by('-vulnerabilidade__cvss', 'pk')[:50]
    return render(request, 'inventario/servico_negocio.html', contexto)
