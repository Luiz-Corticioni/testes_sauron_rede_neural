"""CRUD web: entrada e apresentação; regras e gravação são serviços comuns."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Count, F, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from inventario.web.forms import (
    AtivoForm,
    DependenciaForm,
    IncidenciaForm,
    SalaForm,
    SoftwareForm,
    VulnerabilidadeForm,
)
from inventario.models import Ativo, Dependencia, Incidencia, Sala, Software, Vulnerabilidade
from inventario.web.paginacao import buscar, filtrar_ativos, opcoes_ativos, paginar
from inventario.aplicacao.servicos import salvar_cadastro, remover_cadastro
from inventario.web.contexto_ativos import barras_ativos, ficha_ativo

# Configuração da interface, não uma segunda fábrica de classes do domínio.
CADASTROS = {
    "ativo": (Ativo, AtivoForm, "ativos", "Ativo"),
    "vulnerabilidade": (
        Vulnerabilidade,
        VulnerabilidadeForm,
        "vulnerabilidades",
        "Vulnerabilidade",
    ),
    "incidencia": (Incidencia, IncidenciaForm, "incidencias", "Incidência"),
    "dependencia": (Dependencia, DependenciaForm, "dependencias", "Dependência"),
    "sala": (Sala, SalaForm, "salas", "Sala ou subsetor"),
    "software": (Software, SoftwareForm, "software", "Software"),
}


@require_http_methods(["GET", "POST"])
def formulario(request, cadastro, pk=None):
    modelo, classe_form, destino, rotulo = CADASTROS[cadastro]
    objeto = get_object_or_404(modelo, pk=pk) if pk is not None else modelo()
    kwargs = {"instance": objeto}
    if cadastro == 'vulnerabilidade' and pk is None and request.method == 'GET' and request.GET.get('cve'):
        from inventario.aplicacao.catalogo_cves import preparar_importacao
        from inventario.infraestrutura.cve_client import IntegracaoCVEError
        try:
            kwargs['initial'], aviso = preparar_importacao(request.GET['cve'])
            messages.info(request, 'Dados da NVD preenchidos para revisão. Escolha a categoria e confira o ID antes de salvar.')
            if aviso:
                messages.warning(request, aviso)
        except (ValueError, IntegracaoCVEError):
            messages.warning(request, 'Consulta não disponível no cache. Consulte novamente a NVD antes de importar.')
    if cadastro in {"ativo", "incidencia"}:
        kwargs["usuario"] = request.user
    form = classe_form(request.POST if request.method == "POST" else None, **kwargs)
    if request.method == "POST" and form.is_valid():
        try:
            salvar_cadastro(form.save(commit=False), request.user)
        except (ValidationError, ValueError, IntegrityError) as erro:
            texto = "; ".join(erro.messages) if isinstance(erro, ValidationError) else str(erro)
            form.add_error(None, texto)
        else:
            messages.success(request, f"{rotulo} {objeto.pk} salvo com auditoria.")
            if cadastro == "ativo":
                return redirect("detalhe_ativo", pk=objeto.pk)
            return redirect(destino)
    return render(
        request,
        "inventario/formulario.html",
        {
            "form": form,
            "titulo": f"{'Editar' if pk is not None else 'Cadastrar'} {rotulo.lower()}",
            "cancelar_url": reverse(destino),
        },
    )


@require_http_methods(["GET", "POST"])
def exclusao(request, cadastro, pk):
    modelo, _, destino, rotulo = CADASTROS[cadastro]
    objeto = get_object_or_404(modelo, pk=pk)
    erro = None
    if request.method == "POST":
        if request.POST.get("confirmar") != "sim":
            erro = "Marque a confirmação para excluir."
        else:
            try:
                remover_cadastro(objeto, request.user)
            except ProtectedError as bloqueio:
                erro = (
                    f"Exclusão bloqueada: {len(bloqueio.protected_objects)} registros protegidos "
                    "fazem referência a este cadastro. Revise os vínculos e o histórico."
                )
            else:
                messages.success(request, f"{rotulo} removido com auditoria.")
                return redirect(destino)
    return render(
        request,
        "inventario/confirmar_exclusao.html",
        {
            "objeto": objeto,
            "rotulo": rotulo,
            "erro": erro,
            "cancelar_url": reverse(destino),
            "cascata": cadastro == "ativo",
        },
    )


def listar_ativos(request):
    qs = buscar(
        Ativo.objects.select_related("sala"),
        request.GET,
        ("id", "nome", "hostname", "fabricante", "responsavel"),
        campo_numerico="id_numerico",
    )
    qs = filtrar_ativos(qs, request.GET)
    contexto = paginar(qs, request) | opcoes_ativos()
    contexto["ativos"] = contexto["pagina"]
    contexto["erro_risco"] = barras_ativos(contexto["ativos"], request.user)
    return render(request, "inventario/ativos.html", contexto)


def detalhe_ativo(request, pk):
    ativo = get_object_or_404(Ativo.objects.select_related("sala"), pk=pk)
    return render(
        request,
        "inventario/ativo_detalhe.html",
        ficha_ativo(ativo, request.user),
    )


def listar_vulnerabilidades(request):
    qs = Vulnerabilidade.objects.select_related("epss_observacao").annotate(total_ativos=Count("ativos")).order_by('-cvss', 'id')
    qs = buscar(qs, request.GET, ("id", "cve_id", "descricao", "categoria"))
    if request.GET.get("categoria") in dict(Vulnerabilidade.CATEGORIAS):
        qs = qs.filter(categoria=request.GET["categoria"])
    if request.GET.get("kev") == "1":
        qs = qs.filter(kev=True)
    from datetime import timedelta
    from django.utils import timezone
    hoje = timezone.now().date()
    estados = {"ausente": Q(epss__isnull=True) | Q(epss_data__isnull=True),
               "atualizado": Q(epss__isnull=False, epss_data__gte=hoje-timedelta(days=2), epss_data__lte=hoje),
               "vencido": Q(epss__isnull=False, epss_data__lt=hoje-timedelta(days=2)),
               "legado": Q(epss__isnull=False, epss_observacao__isnull=True)}
    if request.GET.get("epss") in estados:
        qs = qs.filter(estados[request.GET["epss"]])
    if request.GET.get("ordem") == "epss":
        qs = qs.order_by(F("epss").desc(nulls_last=True), "id")
    contexto = paginar(qs, request)
    contexto["estados_epss"] = [("ausente", "Sem dados completos"), ("atualizado", "Atualizado"), ("vencido", "Desatualizado"), ("legado", "Origem não registrada")]
    from inventario.aplicacao.epss import situacao_epss
    for v in contexto["pagina"]:
        v.epss_situacao = situacao_epss(v)
        v.epss_percentual = v.epss * 100 if v.epss is not None else None
        v.epss_percentil = v.epss_observacao.percentil * 100 if v.epss_observacao else None
    contexto.update(vulnerabilidades=contexto["pagina"], categorias=Vulnerabilidade.CATEGORIAS)
    return render(request, "inventario/vulnerabilidades.html", contexto)


def listar_relacoes(request, cadastro):
    modelo, _, _, rotulo = CADASTROS[cadastro]
    qs = modelo.objects.order_by("pk")
    contexto = {}
    if cadastro == "incidencia":
        qs = qs.select_related("ativo", "vulnerabilidade")
        qs = buscar(
            qs,
            request.GET,
            ("id", "ativo__hostname", "vulnerabilidade__id", "vulnerabilidade__cve_id"),
        )
        qs = filtrar_ativos(qs, request.GET, "ativo__")
        if request.GET.get("situacao") in dict(Incidencia.STATUS):
            qs = qs.filter(status=request.GET["situacao"])
        cabecalho = ["ID", "Ativo", "Vulnerabilidade", "CVSS", "Status"]
        exibir = lambda i: [
            i.pk,
            i.ativo.hostname,
            i.vulnerabilidade_id,
            i.vulnerabilidade.cvss,
            i.get_status_display(),
        ]
        contexto = opcoes_ativos() | {"situacoes": Incidencia.STATUS}
    elif cadastro == "dependencia":
        qs = qs.select_related("dependente", "fornecedor")
        qs = buscar(qs, request.GET, ("dependente__hostname", "fornecedor__hostname", "descricao"))
        qs = filtrar_ativos(qs, request.GET, "dependente__")
        cabecalho = ["ID", "Dependente i", "Fornecedor j", "Peso A[i,j]", "Descrição"]
        exibir = lambda d: [d.pk, d.dependente.hostname, d.fornecedor.hostname, d.peso, d.descricao]
        contexto = opcoes_ativos()
    else:
        qs = buscar(qs.select_related("parent"), request.GET, ("id", "nome", "categoria"))
        cabecalho = ["ID", "Nome", "Setor pai", "Tipos permitidos", "Restrita"]
        exibir = lambda s: [
            s.pk,
            s.nome,
            s.parent_id or "Raiz",
            ", ".join(s.tipos_permitidos) or "Todos",
            "Sim" if s.restrita else "Não",
        ]
    if cadastro == "incidencia" and request.user.has_perms(("inventario.view_ativo", "inventario.view_vulnerabilidade")):
        from django.db.models import OuterRef, Subquery
        from inventario.models import AvaliacaoSSVC
        qs = qs.annotate(ultima_ssvc=Subquery(AvaliacaoSSVC.objects.filter(incidencia_id=OuterRef("pk")).values("resultado__rotulo")[:1]))
        cabecalho = [*cabecalho, "Último SSVC registrado (conferir validade)"]
        exibir_base = exibir
        exibir = lambda o: [*exibir_base(o), o.ultima_ssvc or "Não avaliado"]
    contexto.update(paginar(qs, request))
    pode = lambda acao: request.user.has_perm(f"inventario.{acao}_{cadastro}")
    contexto.update(
        titulo="Salas e subsetores" if cadastro == "sala" else rotulo + "s",
        cabecalho=cabecalho,
        linhas=[
            {
                "valores": exibir(o),
                "editar": reverse(f"editar_{cadastro}", args=[o.pk]),
                "remover": reverse(f"remover_{cadastro}", args=[o.pk]),
                "ssvc": reverse("ssvc_incidencia", args=[o.pk]) if cadastro == "incidencia" else None,
            }
            for o in contexto["pagina"]
        ],
        criar_url=reverse(f"criar_{cadastro}"),
        pode_criar=pode("add"),
        pode_editar=pode("change"),
        pode_remover=pode("delete"),
        cadastro=cadastro,
    )
    return render(request, "inventario/relacoes.html", contexto)


def criar_ativo(request):
    return formulario(request, "ativo")


def criar_vulnerabilidade(request):
    return formulario(request, "vulnerabilidade")
