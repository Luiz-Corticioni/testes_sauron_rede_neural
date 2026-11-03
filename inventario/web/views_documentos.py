"""Interface de documentos: leitura paginada; escrita autorizada e sem rede."""
from django import forms
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Prefetch
from django.http import HttpResponse
import hashlib
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_GET
from inventario.aplicacao.documentos import importar, reconciliar, ESCRITA
from inventario.dominio.documentos import MAX_BYTES
from inventario.models import Ativo, DocumentoInventario
from inventario.web.paginacao import paginar


class ImportacaoDocumento(forms.Form):
    ativo = forms.ModelChoiceField(queryset=Ativo.objects.all())
    arquivo = forms.FileField(label="CycloneDX ou OpenVEX JSON, até 2 MB")
    escopo = forms.CharField(max_length=200, label="Aplicação/implantação descrita")
    origem = forms.CharField(max_length=200, label="Origem declarada (ferramenta ou fornecedor)")
    aplicar = forms.BooleanField(required=False, label="Gravar após validar (desmarcado: apenas prévia)")

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if arquivo.size > MAX_BYTES:
            raise forms.ValidationError("Arquivo excede 2 MB.")
        return arquivo


@require_http_methods(["GET", "POST"])
def lista(request):
    pode = request.user.has_perms(ESCRITA)
    if request.method == "POST" and not pode:
        raise PermissionDenied
    form = ImportacaoDocumento(request.POST if request.method == "POST" else None, request.FILES or None,
                              initial={"ativo": request.GET.get("ativo")})
    resultado = None
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            resultado = importar(d["ativo"].pk, d["arquivo"].read(MAX_BYTES+1), request.user, d["escopo"], d["origem"], d["aplicar"])
        except (ValueError, ValidationError) as erro:
            form.add_error(None, erro)
    docs = DocumentoInventario.objects.select_related("ativo", "importado_por").defer("conteudo")
    if request.GET.get("ativo"):
        docs = docs.filter(ativo_id=request.GET["ativo"])
    return render(request, "inventario/documentos.html", {**paginar(docs, request), "form": form, "resultado": resultado, "pode_importar": pode})


@require_http_methods(["GET", "POST"])
def detalhe(request, pk):
    doc = get_object_or_404(DocumentoInventario.objects.select_related("ativo", "importado_por").defer("conteudo"), pk=pk)
    resultado = None
    erro = None
    pode = request.user.has_perms(ESCRITA)
    if request.method == "POST":
        if not pode:
            raise PermissionDenied
        try:
            resultado = {"vinculados": reconciliar(doc, request.user)}
        except (ValueError, ValidationError) as exc:
            erro = str(exc)
    componentes = paginar(doc.componentes.select_related("software").order_by("pk"), request)
    return render(request, "inventario/documento.html", {**componentes, "doc": doc, "pode_importar": pode,
        "declaracoes": doc.declaracoes.order_by("pk"), "achados": doc.achados.select_related("software", "incidencia").prefetch_related(Prefetch("fontes",
            queryset=DocumentoInventario.objects.only("id", "origem", "escopo", "importado_em").order_by("-importado_em", "-pk")[:5], to_attr="fontes_resumo")), "resultado": resultado, "erro": erro})


@require_GET
def baixar(request, pk):
    doc = get_object_or_404(DocumentoInventario, pk=pk)
    canonico = doc.conteudo
    if hashlib.sha256(canonico.encode()).hexdigest() != doc.sha256:
        return HttpResponse("Integridade do documento divergente; consulte a auditoria.", status=409)
    resposta = HttpResponse(canonico, content_type="application/json")
    resposta["Content-Disposition"] = f'attachment; filename="documento-{doc.pk}.json"'
    return resposta
