"""Formulários: notação e validação de entrada; a gravação pertence aos serviços."""

from django import forms
from inventario.models import Ativo, Dependencia, Incidencia, Sala, Software, Vulnerabilidade


class AtivoForm(forms.ModelForm):
    class Meta:
        model = Ativo
        fields = [
            "tipo",
            "nome",
            "hostname",
            "fabricante",
            "modelo",
            "ip",
            "sistema_operacional",
            "versao",
            "responsavel",
            "sala",
            "criticidade",
            "status",
            "fim_suporte",
            "atributos",
            "confidencialidade",
            "integridade",
            "disponibilidade",
            "exposto_internet",
            "zona_rede",
            "portas_servicos",
            "contato",
            "alocacao_excepcional_autorizada",
            "justificativa_excecao",
        ]
        widgets = {"fim_suporte": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})}
        help_texts = {
            "hostname": "Vazio no cadastro: SAU-TIPO-FABRICANTE-00001. Comece com letra.",
            "atributos": 'Objeto JSON, ex.: {"administracao_remota": true}. Vazio: {}.',
            "portas_servicos": "Lista JSON, ex.: "
            '[{"porta":443,"protocolo":"tcp","servico":"https"}].',
            "criticidade": "1 baixo · 2 médio · 3 alto · 4 crítico.",
            "sala": "A sala define os tipos permitidos. Exceções exigem permissão e justificativa.",
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if not self.instance._state.adding:
            self.fields["tipo"].disabled = True
            self.fields["tipo"].help_text = "O tipo integra o ID; para mudar, cadastre outro ativo."
        if not usuario or not usuario.has_perm("inventario.autorizar_alocacao_excepcional"):
            self.fields["alocacao_excepcional_autorizada"].disabled = True
            self.fields["justificativa_excecao"].disabled = True

    def clean(self):
        dados = super().clean()
        # O ModelForm chama Model.clean antes de save: preencher o autor nesta etapa.
        if dados.get("alocacao_excepcional_autorizada") and self.usuario:
            if self.usuario.has_perm("inventario.autorizar_alocacao_excepcional"):
                self.instance.autorizado_por = self.usuario
        return dados


class VulnerabilidadeForm(forms.ModelForm):
    class Meta:
        model = Vulnerabilidade
        fields = [
            "id",
            "cve_id",
            "descricao",
            "categoria",
            "cvss",
            "cvss_versao",
            "cvss_vetor",
            "fonte",
            "publicada_em",
        ]
        widgets = {
            "publicada_em": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "cve_id": forms.TextInput(attrs={"data-autocomplete-cve": "", "placeholder": "CVE ou nome da falha"}),
        }
        help_texts = {
            "id": "VUL-TIPO-0001. Tipos: RCE, AUTH, DOS, INFO, PRIV, INJ, CFG, OUTRA.",
            "cve_id": "Opcional: CVE-AAAA-NNNN, por exemplo CVE-2021-44228.",
            "cvss": "De 0 a 10. O vetor preenchido é recalculado para evitar inconsistência.",
            "cvss_vetor": "Ex.: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields["id"].disabled = True

    def clean_cve_id(self):
        from inventario.dominio.autocomplete import normalizar_cve
        texto = self.cleaned_data.get('cve_id') or ''
        return normalizar_cve(texto) if texto else ''


class IncidenciaForm(forms.ModelForm):
    class Meta:
        model = Incidencia
        fields = [
            "ativo",
            "vulnerabilidade",
            "status",
            "detectada_em",
            "versao_afetada",
            "software",
            "evidencia",
            "observacoes",
            "justificativa",
            "aceita_ate",
        ]
        widgets = {
            nome: forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}) for nome in ("detectada_em", "aceita_ate")
        }
        help_texts = {
            "ativo": "O ID INC é gerado ao salvar. Um mesmo CVE pode afetar vários ativos.",
            "status": "SUGERIDA ainda não confirma a falha. ACEITA requer autorização e prazo.",
            "justificativa": "Obrigatória para aceitar risco; explique a decisão.",
        }

    def __init__(self, *args, usuario=None, ativo_fixo=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        if ativo_fixo is not None:
            self.instance.ativo = ativo_fixo
            self.initial["ativo"] = ativo_fixo.pk
            self.fields["ativo"].disabled = True
            self.fields["status"].help_text = (
                "Aguardando confirmação não entra no cálculo. Escolha Aberta apenas após "
                "verificar produto e versão; a consulta da CVE não comprova a falha no ativo."
            )
        if not self.instance._state.adding:
            self.fields["ativo"].disabled = self.fields["vulnerabilidade"].disabled = True
        if usuario and not usuario.has_perm("inventario.add_incidencia"):
            for nome in ("detectada_em", "versao_afetada", "observacoes", "software"):
                self.fields[nome].disabled = True

    def clean(self):
        dados = super().clean()
        if not self.errors and self.usuario:
            from inventario.aplicacao.decisoes import preparar_formulario
            return preparar_formulario(self.instance,dados,self.usuario)
        return dados


class DependenciaForm(forms.ModelForm):
    class Meta:
        model = Dependencia
        fields = ["dependente", "fornecedor", "peso", "descricao"]
        help_texts = {
            "peso": "A[i,j] transmite risco do fornecedor j ao dependente i. "
            "Use ponto decimal (0.5); a soma da linha deve ser menor que 1."
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields["dependente"].disabled = self.fields["fornecedor"].disabled = True


class SalaForm(forms.ModelForm):
    class Meta:
        model = Sala
        fields = ["id", "nome", "categoria", "parent", "tipos_permitidos", "restrita"]
        help_texts = {
            "id": "Ex.: SALA-TI-001. IDs existentes continuam válidos.",
            "parent": "Selecione a sala ou setor que contém esta sala. Vazio: raiz.",
            "tipos_permitidos": 'Lista JSON de códigos: ["1","4","5"]. [] permite todos.',
            "restrita": "Qualquer alocação passa a exigir autorização excepcional. "
            "Criar sala ou mudar sua política exige a permissão especial.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance._state.adding:
            self.fields["id"].disabled = True
            self.fields["parent"].queryset = Sala.objects.exclude(pk=self.instance.pk)


class SoftwareForm(forms.ModelForm):
    class Meta:
        model = Software
        fields = ["ativo", "nome", "versao", "fornecedor", "purl", "cpe23"]


class ImportarCSVForm(forms.Form):
    arquivo = forms.FileField(label="Arquivo CSV (UTF-8, até 1 MB)")
    aplicar = forms.BooleanField(required=False, label="Gravar o lote após validar")

    def clean_arquivo(self):
        arquivo = self.cleaned_data["arquivo"]
        if arquivo.size > 1024 * 1024:
            raise forms.ValidationError("CSV excede 1 MB.")
        return arquivo
