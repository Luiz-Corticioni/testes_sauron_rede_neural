from django import forms
from inventario.matematica.montecarlo_v2 import FATORES


class CenarioV2Form(forms.Form):
    escopo = forms.ChoiceField(label="Perímetro de rede")
    origem_ativo = forms.ChoiceField(label="Ativo de origem no grafo")
    incidencias = forms.MultipleChoiceField(label="Incidências a considerar", help_text="Use as mesmas faixas para todas as incidências selecionadas.")
    n = forms.IntegerField(label="Simulações", min_value=100, max_value=100000, initial=1000)
    seed = forms.IntegerField(label="Semente", min_value=0, max_value=2**32-1, initial=42)
    correlacao = forms.FloatField(label="Correlação latente hipotética", min_value=0, max_value=1, initial=0,
                                 help_text="Zero assume independência; valores positivos são hipóteses, não medidas automáticas.")
    custo_c = forms.FloatField(label="Perda fixa de confidencialidade (R$)", min_value=0, max_value=1e15)
    custo_i = forms.FloatField(label="Perda fixa de integridade (R$)", min_value=0, max_value=1e15)
    custo_a = forms.FloatField(label="Perda fixa de disponibilidade (R$)", min_value=0, max_value=1e15)
    limite = forms.FloatField(label="Limite de perda do apetite (R$)", min_value=0, max_value=1e15, required=False)
    tolerada = forms.FloatField(label="Probabilidade tolerada acima do limite (0 a 1)", min_value=0, max_value=1, required=False)
    comparar = forms.BooleanField(label="Comparar correção das incidências selecionadas", required=False)
    custo_intervencao = forms.FloatField(label="Custo da correção (R$)", min_value=0, max_value=1e15, required=False)
    sensibilidade = forms.BooleanField(label="Calcular sensibilidade das faixas", required=False)
    calibrar = forms.BooleanField(label="Ajustar custos com perdas declaradas de incidentes encerrados", required=False,
                                  help_text="Exige pelo menos dez perdas por categoria. O ajuste é heurístico e não comprova representatividade.")

    def __init__(self, *args, perimetros, ativos, incidencias, pode_calibrar=False, **kwargs):
        super().__init__(*args, **kwargs)
        if not pode_calibrar:
            self.fields.pop("calibrar")
        self.fields["escopo"].choices = [(p.nome, p.nome) for p in perimetros]
        self.fields["origem_ativo"].choices = [(a.pk, f"{a.pk} — {a.nome}") for a in ativos]
        self.fields["incidencias"].choices = [(i.pk, f"{i.pk} — {i.ativo.nome} — {i.vulnerabilidade.cve_id or i.vulnerabilidade_id}") for i in incidencias]
        titulos = {"exploracao": "Exploração possível", "alcance": "Alcance condicional", "falha_controle": "Falha de controle condicional"}
        for fator in FATORES:
            for parte, nome in (("min", "mínimo"), ("moda", "mais provável"), ("max", "máximo")):
                self.fields[f"{fator}_{parte}"] = forms.FloatField(label=f"{titulos[fator]} — {nome} (0 a 1)", min_value=0, max_value=1)
            self.fields[f"{fator}_origem"] = forms.CharField(label=f"{titulos[fator]} — origem da hipótese", max_length=300)

    def clean(self):
        dados = super().clean()
        for fator in FATORES:
            valores = [dados.get(f"{fator}_{p}") for p in ("min", "moda", "max")]
            if all(v is not None for v in valores) and not valores[0] <= valores[1] <= valores[2]:
                self.add_error(f"{fator}_moda", "Use mínimo ≤ mais provável ≤ máximo.")
        if (dados.get("limite") is None) != (dados.get("tolerada") is None):
            raise forms.ValidationError("Para o apetite, informe limite e probabilidade tolerada juntos.")
        if dados.get("comparar") and dados.get("custo_intervencao") is None:
            self.add_error("custo_intervencao", "Informe o custo para comparar a intervenção.")
        return dados
