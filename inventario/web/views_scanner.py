from django import forms
from django.contrib import messages
from django.core import signing
from django.core.exceptions import ValidationError
from django.db.models import Max, Subquery
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from inventario.aplicacao.scanner import LIMITE, extrair_relatorio, gravar, revisar
from inventario.models import Ativo, RelatorioScanner, RevisaoAchadoScanner
from inventario.web.paginacao import paginar


class ScannerForm(forms.Form):
    ativo = forms.ModelChoiceField(queryset=Ativo.objects.all())
    escopo = forms.CharField(max_length=200, label="Escopo examinado")
    origem = forms.CharField(max_length=200, label="Origem do relatório")
    formato = forms.ChoiceField(choices=[('trivy', 'Trivy JSON'), ('osv', 'OSV-Scanner JSON')], required=False, initial='trivy')
    observado_em = forms.CharField(required=False, max_length=40, label='Data observada (OSV)',
        help_text='Para OSV, declare a data da varredura com fuso, por exemplo 2026-11-18T10:30:00-03:00. Para Trivy, usa-se a data do arquivo.')
    arquivo = forms.FileField(label="Relatório JSON (até 2 MB)")
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
            formato = dados['formato'] or 'trivy'
            data, achados, ignorados, assinatura = extrair_relatorio(conteudo, formato, dados['observado_em'])
            vinculo = {"usuario": request.user.pk, "ativo": dados["ativo"].pk, "escopo": dados["escopo"],
                       "origem": dados["origem"], "sha256": assinatura, "formato": formato, "observado_em": dados['observado_em']}
            if dados["confirmacao"]:
                try:
                    validado = signing.loads(dados["confirmacao"], salt="scanner-previa", max_age=600)
                except signing.BadSignature as erro:
                    raise ValidationError("Prévia inválida ou expirada; gere outra.") from erro
                if validado != vinculo:
                    raise ValidationError("O relatório ou seu contexto mudou; gere outra prévia.")
                relatorio, novo = gravar(dados["ativo"].pk, dados["escopo"], dados["origem"], conteudo, request.user,
                                         formato=formato, observado_em=dados['observado_em'])
                messages.success(request, "Relatório registrado para revisão." if novo else "Relatório já importado.")
                return redirect("scanner_detalhe", pk=relatorio.pk)
            previa = {"data": data, "achados": achados, "ignorados": ignorados, "formato": formato,
                      "data_futura": data > timezone.now()}
            form = ScannerForm(initial={"ativo": dados["ativo"], "escopo": dados["escopo"], "origem": dados["origem"],
                                        "formato": formato, "observado_em": dados['observado_em'],
                                        "confirmacao": signing.dumps(vinculo, salt="scanner-previa")})
        except ValidationError as erro:
            form.add_error(None, erro)
    return render(request, "inventario/scanner.html", {"form": form, "previa": previa,
        "relatorios": RelatorioScanner.objects.select_related("ativo").all()[:50]})


@require_GET
def detalhe(request, pk):
    relatorio = get_object_or_404(RelatorioScanner.objects.select_related("ativo", "importado_por"), pk=pk)
    ultimas = relatorio.revisoes.order_by().values("indice").annotate(ultimo=Max("pk")).values("ultimo")
    revisoes = dict(RevisaoAchadoScanner.objects.filter(pk__in=Subquery(ultimas)).values_list("indice", "classificacao"))
    escolhas = [("TODOS", "Todos"), ("PENDENTE", "Sem revisão"), *RevisaoAchadoScanner.CLASSIFICACOES]
    filtro = request.GET.get("estado", "TODOS")
    if filtro not in dict(escolhas):
        filtro = "TODOS"
    linhas = [{**item, "indice": indice, "estado": revisoes.get(indice, "PENDENTE")}
              for indice, item in enumerate(relatorio.achados)]
    for item in linhas:
        item["estado_rotulo"] = dict(escolhas).get(item["estado"], "Desconhecido")
    resumo = {chave: sum(item["estado"] == chave for item in linhas) for chave, _ in escolhas if chave != "TODOS"}
    if filtro != "TODOS":
        linhas = [item for item in linhas if item["estado"] == filtro]
    return render(request, "inventario/scanner_detalhe.html", {"relatorio": relatorio, "escolhas": escolhas,
        "estado": filtro, "resumo": resumo, **paginar(linhas, request)})


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
