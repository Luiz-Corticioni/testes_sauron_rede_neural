from django.contrib import admin
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.contrib.auth.models import Group
from django.contrib.auth.forms import UserCreationForm

from inventario.models import (
    Ativo,
    CertificadoDigital,
    Dependencia,
    Incidencia,
    Incidente,
    HistoricoIncidencia,
    RegistroAuditoria,
    Sala,
    SnapshotRisco,
    Vulnerabilidade,
    Software,
    Alerta,
    Anticorpo,
    Tolerancia,
    SugestaoImune,
)


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    """A administração também não libera uma nova política sem autorização especial."""

    def has_add_permission(self, request):
        return super().has_add_permission(request) and request.user.has_perm(
            "inventario.autorizar_alocacao_excepcional"
        )

    def get_readonly_fields(self, request, obj=None):
        campos = ("id",) if obj else ()
        if not request.user.has_perm("inventario.autorizar_alocacao_excepcional"):
            campos += ("parent", "tipos_permitidos", "restrita")
        return campos

    def save_model(self, request, obj, form, change):
        from inventario.aplicacao.servicos import salvar_cadastro

        salvar_cadastro(obj, request.user)


@admin.register(Ativo)
class AtivoAdmin(admin.ModelAdmin):
    list_display = ("id_numerico", "id", "hostname", "tipo", "fabricante", "sala", "criticidade", "status")
    readonly_fields = ("id_numerico", "autorizado_por", "alocacao_excepcional_autorizada", "linha_base_saudavel")

    def get_urls(self):
        from django.urls import path
        return [path("<path:object_id>/linha-base/",self.admin_site.admin_view(self.declarar_linha_base),
                     name="inventario_ativo_linha_base")]+super().get_urls()

    def get_list_display(self,request):
        campos=super().get_list_display(request)
        return (*campos,"declaracao") if request.user.has_perm("inventario.declarar_linha_base_saudavel") else campos

    @admin.display(description="Linha de base")
    def declaracao(self,obj):
        from django.urls import reverse
        from django.utils.html import format_html
        return format_html('<a href="{}">Declarar/revogar</a>',
                           reverse("admin:inventario_ativo_linha_base",args=[obj.pk]))

    def declarar_linha_base(self,request,object_id):
        from django import forms
        from django.core.exceptions import PermissionDenied
        from django.shortcuts import get_object_or_404,redirect,render
        from django.urls import reverse
        from inventario.aplicacao.cadastros import salvar_cadastro
        if not request.user.has_perm("inventario.declarar_linha_base_saudavel") or not request.user.has_perm("inventario.change_ativo"):
            raise PermissionDenied("Declaração exige permissão específica.")
        ativo=get_object_or_404(Ativo,pk=object_id)
        class Declaracao(forms.Form):
            saudavel=forms.BooleanField(required=False,label="Declarar saudável (desmarque para revogar)")
            evidencia_scan=forms.CharField(required=False,widget=forms.Textarea,label="Evidência/ID do scan",max_length=8000)

            def clean(self):
                dados=super().clean()
                if dados.get("saudavel") and not dados.get("evidencia_scan","").strip():
                    self.add_error("evidencia_scan","Informe a evidência/ID do scan.")
                return dados
        form=Declaracao(request.POST if request.method=="POST" else None,initial={
            "saudavel":ativo.linha_base_saudavel,"evidencia_scan":ativo.evidencia_scan})
        if request.method=="POST" and form.is_valid():
            ativo.linha_base_saudavel=form.cleaned_data["saudavel"]
            if ativo.linha_base_saudavel:
                ativo.evidencia_scan=form.cleaned_data["evidencia_scan"]
            salvar_cadastro(ativo,request.user)
            return redirect(reverse("admin:inventario_ativo_changelist"))
        return render(request,"inventario/admin_linha_base.html",
            {**self.admin_site.each_context(request),"form":form,"title":"Declaração de linha de base","ativo":ativo})

    def get_readonly_fields(self, request, obj=None):
        campos = self.readonly_fields
        if not request.user.has_perm("inventario.declarar_linha_base_saudavel"):
            campos += ("linha_base_saudavel", "evidencia_scan")
        return campos

    def has_change_permission(self, request, obj=None):
        return (super().has_change_permission(request, obj) and
                (not obj or not obj.linha_base_saudavel or
                 request.user.has_perm("inventario.declarar_linha_base_saudavel")))

    def save_model(self, request, obj, form, change):
        from inventario.aplicacao.cadastros import salvar_cadastro
        salvar_cadastro(obj, request.user)

    list_filter = ("tipo", "status", "criticidade", "sala")
    search_fields = ("=id_numerico", "id", "hostname", "nome", "fabricante", "responsavel")


@admin.register(Vulnerabilidade)
class VulnerabilidadeAdmin(admin.ModelAdmin):
    list_display = ("id", "cve_id", "categoria", "cvss", "severidade", "kev")
    readonly_fields = ("kev", "kev_adicionada_em", "kev_prazo", "uso_ransomware", "epss", "epss_data", "epss_observacao")
    list_filter = ("categoria", "fonte")
    search_fields = ("id", "cve_id", "descricao")

    def get_readonly_fields(self, request, obj=None):
        return (*self.readonly_fields, "id") if obj else self.readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        import re
        base = super().get_form(request, obj, **kwargs)

        class FormVulnerabilidade(base):
            def clean(self):
                dados = super().clean()
                codigo = dados.get("id", self.instance.pk or "")
                categoria = dados.get("categoria", "")
                if codigo and categoria and not re.fullmatch(r"VUL-" + re.escape(categoria) + r"-\d{4,}", codigo.upper()):
                    self.add_error(None, "ID deve corresponder à categoria, por exemplo VUL-RCE-0001.")
                vetor = dados.get("cvss_vetor", "")
                if vetor and dados.get("cvss_versao") == "3.1":
                    from inventario.matematica.cvss import CalculadoraCVSS31
                    try:
                        dados["cvss"] = CalculadoraCVSS31.calcular(vetor).score
                    except ValueError as erro:
                        self.add_error("cvss_vetor", str(erro))
                return dados
        return FormVulnerabilidade

    def save_model(self, request, obj, form, change):
        from inventario.aplicacao.cadastros import salvar_cadastro
        salvar_cadastro(obj, request.user)


@admin.register(Incidencia)
class IncidenciaAdmin(admin.ModelAdmin):
    readonly_fields = ("aceita_por", "imune_aprendida", "solicitada_por", "aprovada_por", "decisao_pendente")

    def save_model(self, request, obj, form, change):
        from inventario.aplicacao.cadastros import salvar_cadastro
        salvar_cadastro(obj, request.user)

    def get_form(self, request, obj=None, **kwargs):
        base = super().get_form(request, obj, **kwargs)

        class FormAceite(base):
            def clean(self):
                dados = super().clean()
                if not self.errors:
                    from inventario.aplicacao.decisoes import preparar_formulario
                    return preparar_formulario(self.instance,dados,request.user)
                return dados

        return FormAceite

    def get_readonly_fields(self, request, obj=None):
        # A permissão de status do operador também vale quando ele é staff.
        if request.user.has_perm("inventario.add_incidencia"):
            return self.readonly_fields
        return tuple(campo.name for campo in Incidencia._meta.fields if campo.name != "status")


@admin.register(RegistroAuditoria)
class RegistroAuditoriaAdmin(admin.ModelAdmin):
    list_display = ("ocorrido_em", "usuario", "acao", "entidade", "entidade_id")
    readonly_fields = ("usuario", "acao", "entidade", "entidade_id", "detalhes", "ocorrido_em")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DerivadosAdmin(RegistroAuditoriaAdmin):
    list_display = ("id",)
    readonly_fields = ()

    def get_readonly_fields(self, request, obj=None):
        return tuple(campo.name for campo in self.model._meta.fields)


class CadastroAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        from inventario.aplicacao.cadastros import salvar_cadastro
        salvar_cadastro(obj, request.user)


admin.site.register([Dependencia, Incidente, CertificadoDigital, Software], CadastroAdmin)
admin.site.register([Alerta, Anticorpo, Tolerancia, SugestaoImune], DerivadosAdmin)
admin.site.register([HistoricoIncidencia, SnapshotRisco], DerivadosAdmin)
admin.site.site_header = "Sauron — APRESENTAÇÃO · MFA DESATIVADO"


# O cadastro de usuários na administração também solicita e valida o e-mail.


class CriacaoUsuarioComEmail(UserCreationForm):
    email = forms.EmailField(label="E-mail", required=True,
        help_text="Será enviado um código de confirmação quando o SMTP estiver configurado.")

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")


class UsuarioComEmailAdmin(UserAdmin):
    add_form = CriacaoUsuarioComEmail
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("username", "email", "password1", "password2")}),)


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), UsuarioComEmailAdmin)


class GestaoIdentidadesRestrita:
    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    has_add_permission = has_view_permission
    has_change_permission = has_view_permission
    has_delete_permission = has_view_permission


class UsuarioRestritoAdmin(GestaoIdentidadesRestrita, UsuarioComEmailAdmin):
    pass




class GrupoRestritoAdmin(GestaoIdentidadesRestrita, GroupAdmin):
    pass


admin.site.unregister(get_user_model())
admin.site.register(get_user_model(), UsuarioRestritoAdmin)
admin.site.unregister(Group)
admin.site.register(Group, GrupoRestritoAdmin)
