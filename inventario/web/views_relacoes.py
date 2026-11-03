"""Consulta por camada e manutenção de relações; sem alterações por GET."""
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from inventario.aplicacao.relacoes import analisar_relacoes, salvar_relacao
from inventario.models import Ativo, RelacaoAtivos
from inventario.web.paginacao import paginar


class RelacaoForm(forms.ModelForm):
    versao = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = RelacaoAtivos
        fields = ["origem", "destino", "tipo", "escopo", "protocolo", "porta", "principal",
                  "privilegio", "fonte", "evidencia", "observada_em", "revisar_em", "vigente"]
        widgets = {c: forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}) for c in ("observada_em", "revisar_em")}
        help_texts = {
            "origem": "Rede: inicia tráfego; identidade: ponto de uso do principal; negócio: fornecedor do serviço.",
            "destino": "Rede: recebe tráfego; identidade: recurso acessado; negócio: consumidor dependente.",
            "evidencia": "Referência verificável ou descrição da verificação; não informe credenciais.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["versao"] = self.instance.atualizado_em.isoformat()


class AnaliseRelacoesForm(forms.Form):
    tipo = forms.ChoiceField(choices=RelacaoAtivos.TIPOS, label="Camada")
    escopo = forms.CharField(max_length=200, label="Escopo exato")
    principal = forms.CharField(max_length=200, required=False, label="Identidade exata (somente camada identidade)")
    origem = forms.ModelChoiceField(queryset=Ativo.objects.exclude(status__in=["INATIVO", "BAIXADO"]), label="Origem")
    destino = forms.ModelChoiceField(queryset=Ativo.objects.exclude(status__in=["INATIVO", "BAIXADO"]), required=False, label="Destino específico (opcional)")
    remover_relacao = forms.IntegerField(min_value=1, required=False, label="Simular retirada da relação de ID")
    remover_ativo = forms.ModelChoiceField(queryset=Ativo.objects.exclude(status__in=["INATIVO", "BAIXADO"]), required=False, label="Simular retirada do ativo")
    limite = forms.IntegerField(min_value=1, max_value=100, initial=50, label="Até quantos destinos exibir")

    def parametros(self):
        d = self.cleaned_data.copy()
        for campo in ("origem", "destino", "remover_ativo"):
            d[campo] = d[campo].pk if d[campo] else None
        return d


@require_GET
def lista(request):
    qs = RelacaoAtivos.objects.select_related("origem", "destino", "atualizada_por")
    if request.GET.get("q"):
        termo = request.GET["q"][:200]
        qs = qs.filter(Q(escopo__icontains=termo) | Q(origem_id__icontains=termo) | Q(destino_id__icontains=termo) | Q(principal__icontains=termo))
    if request.GET.get("tipo") in dict(RelacaoAtivos.TIPOS):
        qs = qs.filter(tipo=request.GET["tipo"])
    return render(request, "inventario/relacoes_tipadas.html", {**paginar(qs, request), "tipos": RelacaoAtivos.TIPOS, "hoje": timezone.localdate()})


@require_http_methods(["GET", "POST"])
def formulario(request, pk=None):
    acao = "change" if pk else "add"
    if not request.user.has_perm(f"inventario.{acao}_relacaoativos"):
        raise PermissionDenied
    obj = get_object_or_404(RelacaoAtivos, pk=pk) if pk else RelacaoAtivos()
    form = RelacaoForm(request.POST if request.method == "POST" else None, instance=obj)
    if request.method == "POST" and form.is_valid():
        dados = {campo: valor for campo, valor in form.cleaned_data.items() if campo != "versao"}
        for campo in ("origem", "destino"):
            dados[campo+"_id"] = dados.pop(campo).pk
        try:
            salvar_relacao(dados, request.user, pk, form.cleaned_data["versao"])
        except (ValidationError, ValueError, IntegrityError) as erro:
            form.add_error(None, "; ".join(erro.messages) if isinstance(erro, ValidationError) else "Conflito no cadastro; confira as relações existentes.")
        else:
            messages.success(request, "Relação salva com evidência e auditoria.")
            return redirect("relacoes")
    return render(request, "inventario/formulario.html", {"form": form, "titulo": "Editar relação" if pk else "Cadastrar relação", "cancelar_url": "/relacoes/"})


@require_GET
def detalhe(request, pk):
    obj = get_object_or_404(RelacaoAtivos.objects.select_related("origem", "destino", "criada_por", "atualizada_por"), pk=pk)
    return render(request, "inventario/relacao_detalhe.html", {"r": obj, "hoje": timezone.localdate()})


@require_GET
def painel(request):
    # GET vazio apresenta formulário; análise só ocorre com parâmetros explícitos.
    form = AnaliseRelacoesForm(request.GET if request.GET else None)
    resultado = None
    if form.is_bound and form.is_valid():
        try:
            resultado = analisar_relacoes(request.user, **form.parametros())
        except ValueError as erro:
            form.add_error(None, erro)
    return render(request, "inventario/grafo_relacoes.html", {"form": form, "resultado": resultado})


@require_GET
def api(request):
    form = AnaliseRelacoesForm(request.GET)
    if not form.is_valid():
        return JsonResponse({"erro": form.errors.get_json_data()}, status=400)
    try:
        return JsonResponse(analisar_relacoes(request.user, **form.parametros()))
    except ValueError as erro:
        return JsonResponse({"erro": str(erro)}, status=400)
