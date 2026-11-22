from unittest import TestCase

from inventario.matematica.montecarlo import simular
from inventario.matematica.montecarlo_v2 import simular_v2
from .base import BancoTeste


def fatores(prob, exposicao=1):
    return {nome: {"faixa": [valor] * 3, "origem": "Hipótese sintética"}
            for nome, valor in (("exploracao", prob), ("alcance", exposicao), ("falha_controle", 1))}


class SimulacaoV2(TestCase):
    def entradas(self, total=2):
        return [{"id": f"INC-{i}", "ativo": f"A-{i}", "cve": "CVE-2025-1111", "cvss": 10,
                 "epss": .1, "vetor": "", "exposicao": .8, "kev": False} for i in range(total)]

    def test_correlacao_zero_e_fatores_fixos_reproduzem_v1(self):
        entradas = self.entradas()
        custos = {"C": 10, "I": 0, "A": 0}
        v1 = simular(entradas, custos=custos, n=1000, seed=3)
        v2 = simular_v2(entradas, {e["id"]: fatores(.1, .8) for e in entradas}, custos=custos, n=1000, seed=3)
        self.assertEqual(v1["antes"], v2["antes"])
        self.assertEqual(v1["depois"], v2["depois"])
        self.assertEqual(v1["excedencia"], v2["excedencia"])

    def test_causa_comum_aumenta_cauda_no_exemplo_e_e_reproduzivel(self):
        entradas = self.entradas(20)
        fatores_ = {e["id"]: fatores(.1, .8) for e in entradas}
        kwargs = {"custos": {"C": 10, "I": 0, "A": 0}, "n": 10000, "seed": 9}
        independente = simular_v2(entradas, fatores_, correlacao=0, **kwargs)
        correlacionado = simular_v2(entradas, fatores_, correlacao=.8, **kwargs)
        self.assertGreater(correlacionado["antes"]["P95"], independente["antes"]["P95"])
        self.assertGreater(correlacionado["antes"]["P99"], independente["antes"]["P99"])
        self.assertEqual(correlacionado, simular_v2(entradas, fatores_, correlacao=.8, **kwargs))

    def test_sem_origem_ou_fator_nao_calcula_e_intervencao_usa_mesmas_amostras(self):
        entradas = self.entradas()
        fatores_ = {e["id"]: fatores(.1, .8) for e in entradas}
        with self.assertRaises(ValueError):
            simular_v2(entradas, {}, n=100)
        fatores_["INC-0"]["alcance"]["origem"] = ""
        with self.assertRaises(ValueError):
            simular_v2(entradas, fatores_, n=100)
        fatores_["INC-0"]["alcance"]["origem"] = "Revisão sintética"
        r = simular_v2(entradas, fatores_, custos={"C": 10, "I": 0, "A": 0}, n=1000,
                       intervencoes=[{"nome": "Corrigir", "incidencias": ["INC-0"], "custo": 5}])
        self.assertGreaterEqual(r["intervencoes"][0]["reducao_media"], 0)
        self.assertGreaterEqual(r["intervencoes"][0]["reducao_p95"], 0)

    def test_apetite_usa_limiar_exato_e_nao_interpreta_percentual_como_certeza(self):
        entradas = self.entradas()
        r = simular_v2(entradas, {e["id"]: fatores(.1) for e in entradas},
                       custos={"C": 10, "I": 0, "A": 0}, n=1000,
                       apetite={"limite": 0, "probabilidade_tolerada": 0})
        self.assertEqual(r["apetite"]["probabilidade_simulada"], r["antes"]["probabilidade_perda"])
        self.assertTrue(r["apetite"]["violado"])

    def test_tornado_varia_faixas_com_as_mesmas_amostras(self):
        entradas = self.entradas()
        fatores_ = {e["id"]: fatores(.1) for e in entradas}
        for item in fatores_.values():
            item["exploracao"]["faixa"] = [.02, .1, .3]
        r = simular_v2(entradas, fatores_, custos={"C": 10, "I": 0, "A": 0}, n=1000, sensibilidade=True)
        exploracao = next(x for x in r["sensibilidade"] if x["fator"] == "exploracao")
        self.assertGreater(exploracao["media_maximo"], exploracao["media_minimo"])
        self.assertEqual(len(r["sensibilidade"]), 3)


class IntegracaoV2(BancoTeste):
    def preparar(self):
        from datetime import timedelta
        from django.utils import timezone
        from inventario.aplicacao.cobertura import salvar_perimetro
        from inventario.aplicacao.relacoes import salvar_relacao
        from inventario.models import ObservacaoEPSS

        hoje = timezone.localdate()
        salvar_perimetro(self.usuario, "Rede demonstrativa", "Ambiente sintético", [self.a.pk, self.b.pk])
        salvar_relacao({"origem_id": self.a.pk, "destino_id": self.b.pk, "tipo": "REDE", "escopo": "Rede demonstrativa",
                        "protocolo": "tcp", "porta": 443, "principal": "", "privilegio": "", "fonte": "Teste",
                        "evidencia": "Caminho declarado", "observada_em": hoje, "revisar_em": hoje + timedelta(days=7),
                        "vigente": True}, self.usuario)
        observacao = ObservacaoEPSS.objects.create(cve_id=self.v.cve_id, data=hoje, epss=.2, percentil=.5, assinatura="a"*64)
        self.v.epss, self.v.epss_data, self.v.epss_observacao = .2, hoje, observacao
        self.v.save()
        return {"origem_ativo": self.a.pk, "escopo": "Rede demonstrativa", "incidencias": [self.i.pk],
                "n": 1000, "fatores": {self.i.pk: fatores(.2, .8)}, "correlacao": .3,
                "custos": {"C": 100, "I": 100, "A": 100}}

    def test_exige_evidencia_e_api_usa_origem_perimetro_e_sessao(self):
        import json
        from inventario.aplicacao.montecarlo_v2 import calcular
        dados = self.preparar()
        ausente = {**dados, "fatores": {}}
        pendente = calcular(self.usuario, ausente)
        self.assertFalse(pendente["disponivel"])
        self.assertEqual(pendente["pendencias_total"], 3)
        origem_ausente = {**dados, "fatores": {self.i.pk: {**dados["fatores"][self.i.pk], "alcance": {"faixa": [.1, .2, .3]}}}}
        self.assertFalse(calcular(self.usuario, origem_ausente)["disponivel"])
        resultado = calcular(self.usuario, dados)
        self.assertTrue(resultado["disponivel"])
        self.assertEqual(resultado["versao_modelo"], "sauron.montecarlo/30d-v2")
        self.assertIsNone(resultado["qualidade_dados"]["score"])
        resposta = self.client.post("/api/montecarlo/v2/", json.dumps(dados), content_type="application/json")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Cache-Control"], "no-store")
        self.assertEqual(resposta.json()["grafo_sha256"], resultado["grafo_sha256"])
        profundo = '[' * 2000 + '0' + ']' * 2000
        self.assertEqual(self.client.post("/api/montecarlo/v2/", profundo, content_type="application/json").status_code, 400)
        self.client.logout()
        self.assertNotEqual(self.client.post("/api/montecarlo/v2/", json.dumps(dados), content_type="application/json").status_code, 200)

    def test_api_exige_relacoes_e_csrf(self):
        import json
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Permission
        from django.test import Client
        dados = self.preparar()
        usuario = get_user_model().objects.create_user("sem-relacoes-v2")
        usuario.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario",
            codename__in=["view_ativo", "view_vulnerabilidade", "view_incidencia", "view_dependencia"]))
        self.autenticar(usuario)
        self.assertEqual(self.client.post("/api/montecarlo/v2/", json.dumps(dados), content_type="application/json").status_code, 403)
        cliente = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, cliente)
        self.assertEqual(cliente.post("/api/montecarlo/v2/", json.dumps(dados), content_type="application/json").status_code, 403)

    def test_ausencia_de_caminho_nunca_e_convertida_em_zero(self):
        from inventario.aplicacao.montecarlo_v2 import calcular
        dados = self.preparar()
        dados["origem_ativo"] = self.b.pk
        resultado = calcular(self.usuario, dados)
        self.assertFalse(resultado["disponivel"])
        self.assertIn("não comprova isolamento", resultado["pendencias"][0]["motivo"])

    def test_epss_ausente_nao_impede_fator_independente_nem_inventa_valor(self):
        from inventario.aplicacao.montecarlo_v2 import calcular
        dados = self.preparar()
        self.v.epss = self.v.epss_data = self.v.epss_observacao = None
        self.v.save()
        resultado = calcular(self.usuario, dados)
        self.assertTrue(resultado["disponivel"])
        self.assertIsNone(resultado["entradas"][0]["epss"])
        self.assertEqual(resultado["entradas"][0]["origem_epss"], "indisponível")
        self.assertEqual(resultado["qualidade_dados"]["componentes"][0]["percentual"], 0)

    def test_formulario_calcula_sem_salvar_cenario(self):
        dados = self.preparar()
        formulario = {"escopo": dados["escopo"], "origem_ativo": dados["origem_ativo"],
            "incidencias": [self.i.pk], "n": "1000", "seed": "42", "correlacao": "0.2",
            "custo_c": "100", "custo_i": "20", "custo_a": "50", "limite": "50", "tolerada": "0.1",
            "comparar": "on", "custo_intervencao": "10", "sensibilidade": "on"}
        for nome, valor in (("exploracao", "0.2"), ("alcance", "0.8"), ("falha_controle", "0.5")):
            for parte in ("min", "moda", "max"):
                formulario[f"{nome}_{parte}"] = valor
            formulario[f"{nome}_origem"] = "Hipótese de teste"
        resposta = self.client.post("/montecarlo/v2/", formulario)
        self.assertContains(resposta, "Perda média")
        self.assertEqual(resposta["Cache-Control"], "no-store")
        self.assertContains(resposta, "Sensibilidade individual")
        self.assertTrue(resposta.context["resultado"]["disponivel"])

    def test_calibracao_exige_dados_permissao_e_invalida_cache(self):
        from datetime import timedelta
        from decimal import Decimal
        from django.contrib.auth import get_user_model
        from django.core.exceptions import PermissionDenied
        from django.utils import timezone
        from inventario.aplicacao.montecarlo_v2 import calcular
        from inventario.aplicacao.perdas_financeiras import registrar
        from inventario.models import Incidente

        dados = self.preparar()
        dados["calibrar"] = True
        demonstracao = Incidente.objects.create(ativo=self.a, titulo="Demonstração", descricao="Sintético",
            aberto_em=timezone.now()-timedelta(days=2), encerrado_em=timezone.now())
        registrar(self.usuario, demonstracao, "C", "SIMULADA", Decimal("1000"), timezone.localdate(), "Exemplo")
        antes = calcular(self.usuario, dados)
        self.assertFalse(antes["calibracao"]["calibrado"])
        self.assertEqual(next(c for c in antes["calibracao"]["categorias"] if c["categoria"] == "C")["observacoes"], 0)
        for i in range(10):
            incidente = Incidente.objects.create(ativo=self.a, titulo=f"Teste {i}", descricao="Sintético",
                aberto_em=timezone.now()-timedelta(days=2), encerrado_em=timezone.now())
            registrar(self.usuario, incidente, "C", "REAL", Decimal(100 + i * 20), timezone.localdate(), "Fixture sintética")
        depois = calcular(self.usuario, dados)
        self.assertTrue(depois["calibracao"]["calibrado"])
        categoria = next(x for x in depois["calibracao"]["categorias"] if x["categoria"] == "C")
        self.assertEqual(categoria["observacoes"], 10)
        self.assertIn("antes", depois["calibracao"])
        self.assertIn("depois", depois["calibracao"])
        sem = get_user_model().objects.create_user("sem-financeiro")
        from inventario.aplicacao.perdas_financeiras import calibrar
        with self.assertRaises(PermissionDenied):
            calibrar(sem, {"C": 1, "I": 1, "A": 1})

    def test_formulario_registra_perda_de_incidente_encerrado(self):
        from datetime import timedelta
        from django.utils import timezone
        from inventario.models import Incidente, PerdaFinanceira
        incidente = Incidente.objects.create(ativo=self.a, titulo="Teste", descricao="Sintético",
            aberto_em=timezone.now()-timedelta(days=1), encerrado_em=timezone.now())
        resposta = self.client.post("/perdas-financeiras/", {"incidente": incidente.pk, "categoria": "C", "natureza": "SIMULADA",
            "valor": "150.00", "data": timezone.localdate().isoformat(), "origem": "Relatório de teste"})
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(PerdaFinanceira.objects.count(), 1)
        self.client.logout()
        self.assertNotEqual(self.client.get("/perdas-financeiras/").status_code, 200)

    def test_grupos_padrao_nao_concedem_perdas_a_operadores_ou_auditores(self):
        from django.contrib.auth.models import Group
        from inventario.management.commands.configurar_grupos import configurar_grupos
        configurar_grupos()
        for nome in ("Operadores", "Auditores"):
            self.assertFalse(Group.objects.get(name=nome).permissions.filter(codename="view_perdafinanceira").exists())
        self.assertTrue(Group.objects.get(name="Gerentes").permissions.filter(codename="view_perdafinanceira").exists())

    def test_incidencia_historica_pode_ser_criada_pela_interface(self):
        from datetime import timedelta
        from django.utils import timezone
        from inventario.models import Incidente
        hoje = timezone.localdate()
        dados = {"ativo": self.a.pk, "titulo": "Interrupção de teste", "descricao": "Incidente sintético",
                 "gravidade": 2, "abertura": (hoje - timedelta(days=3)).isoformat(),
                 "encerramento": (hoje - timedelta(days=1)).isoformat()}
        resposta = self.client.post("/perdas-financeiras/incidente/", dados)
        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(Incidente.objects.filter(titulo="Interrupção de teste", encerrado_em__isnull=False).exists())
        dados["encerramento"] = (hoje + timedelta(days=1)).isoformat()
        self.assertContains(self.client.post("/perdas-financeiras/incidente/", dados), "não podem ser futuras")
