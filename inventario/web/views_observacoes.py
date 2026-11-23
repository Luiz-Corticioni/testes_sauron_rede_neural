from django import forms
from django.conf import settings
from django.contrib import messages
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import OuterRef, Subquery
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from inventario.aplicacao.observacoes import importar, preparar, registrar_falha, revisar
from inventario.dominio.observacoes import FORMATOS, LIMITE_BYTES
from inventario.models import ObservacaoImportada, RevisaoObservacao
from inventario.web.paginacao import paginar


class ImportacaoForm(forms.Form):
    formato = forms.ChoiceField(choices=[(x, x.replace("_", " ").upper()) for x in FORMATOS], label="Formato do arquivo")
    fonte = forms.CharField(max_length=120, label="Identidade da fonte", help_text="Um identificador estável, sem URL, e-mail ou credenciais.")
    versao = forms.CharField(max_length=120, label="Versão da fonte", help_text="Versão declarada do exportador ou perfil, sem segredos.")
    observado_em = forms.CharField(max_length=40, label="Data observada com fuso", help_text="Exemplo: 2026-11-20T14:30:00-03:00.")
    confianca = forms.ChoiceField(choices=ObservacaoImportada.CONFIANCAS, label="Confiança declarada")
    arquivo = forms.FileField(label="Arquivo offline (até 2 MiB)")
    confirmacao = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if arquivo.size > LIMITE_BYTES:
            raise forms.ValidationError("Arquivo excede 2 MiB.")
        return arquivo


@require_http_methods(["GET", "POST"])
def importar_web(request):
    form = ImportacaoForm(request.POST or None, request.FILES or None)
    previa = None
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        conteudo = d["arquivo"].read(LIMITE_BYTES + 1)
        gravacao_iniciada = False
        try:
            parametros = {k: d[k] for k in ("formato", "fonte", "versao", "observado_em", "confianca")}
            previa = preparar(conteudo=conteudo, usuario=request.user, **parametros)
            vinculo = {**parametros, "usuario": request.user.pk, "arquivo_sha256": previa["arquivo_sha256"]}
            if d["confirmacao"]:
                try:
                    validado = signing.loads(d["confirmacao"], salt="observacoes-previa-v1", max_age=600)
                except signing.BadSignature as erro:
                    raise ValidationError("Prévia inválida ou expirada; gere outra.") from erro
                if validado != vinculo:
                    raise ValidationError("Arquivo ou contexto mudou; gere outra prévia.")
                gravacao_iniciada = True
                r = importar(conteudo=conteudo, usuario=request.user, **parametros)
                messages.success(request, f"Importadas: {r['novos']}; já existentes: {r['repetidos']}; ignoradas: {r['ignorados']}.")
                return redirect("observacoes_lista")
            previa = {**previa, "total": len(previa["itens"]), "itens": previa["itens"][:20]}
            form = ImportacaoForm(initial={**parametros, "confirmacao": signing.dumps(vinculo, salt="observacoes-previa-v1")})
        except (ValidationError, IntegrityError) as erro:
            if not gravacao_iniciada:
                registrar_falha(d["formato"], request.user)
            form.add_error(None, erro if isinstance(erro, ValidationError) else "Conflito na importação; nenhuma alteração foi salva.")
    resposta = render(request, "inventario/observacoes_importar.html", {"form": form, "previa": previa,
        "habilitado": settings.SAURON_IMPORTACAO_OBSERVACOES_ENABLED})
    resposta["Cache-Control"] = "no-store"
    return resposta


@require_GET
def lista(request):
    ultima = RevisaoObservacao.objects.filter(observacao_id=OuterRef("pk")).order_by("-pk")
    qs = ObservacaoImportada.objects.annotate(ultima_classificacao=Subquery(ultima.values("classificacao")[:1]))
    resposta = render(request, "inventario/observacoes_lista.html", paginar(qs, request))
    resposta["Cache-Control"] = "no-store"
    return resposta


@require_GET
def api_detalhe(request, pk):
    item = get_object_or_404(ObservacaoImportada, pk=pk)
    resposta = JsonResponse({"versao": item.versao_contrato, "origem": item.formato, "tipo": item.tipo,
        "identidade_fonte": item.identidade_fonte, "versao_fonte": item.versao_fonte,
        "identificador": item.identificador, "observado_em": item.observado_em.isoformat(),
        "recebido_em": item.recebido_em.isoformat(), "confianca": item.confianca,
        "erro": item.erro or None, "conteudo_sha256": item.conteudo_sha256, "dados": item.dados})
    resposta["Cache-Control"] = "no-store"
    return resposta


class RevisaoForm(forms.Form):
    classificacao = forms.ChoiceField(choices=RevisaoObservacao.CLASSIFICACOES)
    justificativa = forms.CharField(max_length=500, widget=forms.Textarea(attrs={"rows": 3}))
    revisar_em = forms.DateField(required=False, label="Revisar relação em", widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Obrigatório ao criar relação; entre amanhã e 90 dias.")


@require_http_methods(["GET", "POST"])
def detalhe(request, pk):
    observacao = get_object_or_404(ObservacaoImportada, pk=pk)
    form = RevisaoForm(request.POST or None)
    pode_revisar = request.user.has_perm("inventario.add_revisaoobservacao")
    if request.method == "POST":
        if not pode_revisar:
            raise PermissionDenied
        if form.is_valid():
            try:
                revisar(pk, form.cleaned_data["classificacao"], form.cleaned_data["justificativa"],
                        request.user, form.cleaned_data["revisar_em"])
            except (ValidationError, IntegrityError, ValueError) as erro:
                form.add_error(None, erro if isinstance(erro, ValidationError) else "Não foi possível registrar; confira dados e relações existentes.")
            else:
                messages.success(request, "Revisão registrada com auditoria.")
                return redirect("observacao_detalhe", pk=pk)
    resposta = render(request, "inventario/observacoes_detalhe.html", {"observacao": observacao, "form": form,
        "pode_revisar": pode_revisar, "revisoes": observacao.revisoes.select_related("autor", "relacao")[:100]})
    resposta["Cache-Control"] = "no-store"
    return resposta
