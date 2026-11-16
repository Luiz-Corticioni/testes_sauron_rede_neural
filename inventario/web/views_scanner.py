from django import forms
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from inventario.aplicacao.scanner import LIMITE, extrair, gravar, revisar
from inventario.models import Ativo, RelatorioScanner, RevisaoAchadoScanner


class ScannerForm(forms.Form):
    ativo = forms.ModelChoiceField(queryset=Ativo.objects.all())
    escopo = forms.CharField(max_length=200, label="Escopo examinado")
    origem = forms.CharField(max_length=200, label="Origem do relatório")
    arquivo = forms.FileField(label="Trivy JSON (até 2 MB)")
    confirmacao = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if arquivo.size > LIMITE:
            raise forms.ValidationError("Arquivo excede 2 MB.")
        return arquivo


@require_http_methods(["GET", "POST"])
def importar(request):
    form = ScannerForm(request.POST or None, request.FILES or None)
    previa = None
    if request.method == "POST" and form.is_valid():
        dados = form.cleaned_data
        try:
            conteudo = dados["arquivo"].read(LIMITE + 1)
            data, achados, ignorados, assinatura = extrair(conteudo)
            vinculo = {"usuario": request.user.pk, "ativo": dados["ativo"].pk, "escopo": dados["escopo"],
                       "origem": dados["origem"], "sha256": assinatura}
            if dados["confirmacao"]:
                try:
                    validado = signing.loads(dados["confirmacao"], salt="scanner-previa", max_age=600)
                except signing.BadSignature as erro:
                    raise ValidationError("Prévia inválida ou expirada; gere outra.") from erro
                if validado != vinculo:
                    raise ValidationError("O relatório ou seu contexto mudou; gere outra prévia.")
                relatorio, novo = gravar(dados["ativo"].pk, dados["escopo"], dados["origem"], conteudo, request.user)
                messages.success(request, "Relatório registrado para revisão." if novo else "Relatório já importado.")
                return redirect("scanner_detalhe", pk=relatorio.pk)
            previa = {"data": data, "achados": achados, "ignorados": ignorados}
            form = ScannerForm(initial={"ativo": dados["ativo"], "escopo": dados["escopo"], "origem": dados["origem"],
                                        "confirmacao": signing.dumps(vinculo, salt="scanner-previa")})
        except ValidationError as erro:
            form.add_error(None, erro)
    return render(request, "inventario/scanner.html", {"form": form, "previa": previa,
        "relatorios": RelatorioScanner.objects.select_related("ativo").all()[:50]})


@require_GET
def detalhe(request, pk):
    return render(request, "inventario/scanner_detalhe.html", {"relatorio": get_object_or_404(RelatorioScanner.objects.select_related("ativo", "importado_por"), pk=pk)})


class RevisaoForm(forms.Form):
    classificacao = forms.ChoiceField(choices=RevisaoAchadoScanner.CLASSIFICACOES)
    justificativa = forms.CharField(max_length=500, label="Justificativa", widget=forms.Textarea(attrs={"rows": 3}))


@require_http_methods(["GET", "POST"])
def revisao(request, pk, indice):
    relatorio = get_object_or_404(RelatorioScanner, pk=pk)
    if indice >= len(relatorio.achados):
        from django.http import Http404
        raise Http404
    form = RevisaoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        revisar(pk, indice, form.cleaned_data["classificacao"], form.cleaned_data["justificativa"], request.user)
        messages.success(request, "Revisão registrada. Nenhuma incidência foi alterada.")
        return redirect("scanner_revisao", pk=pk, indice=indice)
    return render(request, "inventario/scanner_revisao.html", {"form": form, "relatorio": relatorio,
        "indice": indice, "achado": relatorio.achados[indice],
        "revisoes": relatorio.revisoes.filter(indice=indice).select_related("autor")[:100]})
