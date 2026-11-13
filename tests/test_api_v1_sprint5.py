from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

from .base import BancoTeste


class ConsultasV1(BancoTeste):
    def test_autenticacao_e_mfa_sao_obrigatorios(self):
        self.client.logout()
        resposta = self.client.get("/api/v1/ativos/")
        self.assertEqual(resposta.status_code, 401)
        self.assertEqual(resposta["Content-Type"], "application/problem+json")
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get("/api/v1/ativos/").status_code, 403)

    def test_paginacao_filtro_e_validacao(self):
        resposta = self.client.get("/api/v1/ativos/", {"tamanho": 1})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["total"], 2)
        self.assertEqual(len(resposta.json()["resultados"]), 1)
        resposta = self.client.get("/api/v1/ativos/", {"busca": "Servidor"})
        self.assertEqual(resposta.json()["resultados"][0]["id"], self.a.pk)
        self.assertEqual(self.client.get("/api/v1/ativos/", {"tamanho": 101}).status_code, 422)
        self.assertEqual(self.client.get("/api/v1/ativos/", {"ordenar": "hostname;drop"}).status_code, 422)

    def test_risco_utiliza_o_modelo_real_e_exige_permissoes(self):
        resposta = self.client.get("/api/v1/ativos/", {"ordenar": "-risco"})
        self.assertEqual(resposta.status_code, 200)
        registros = resposta.json()["resultados"]
        self.assertGreaterEqual(registros[0]["risco_efetivo"], registros[1]["risco_efetivo"])
        u = get_user_model().objects.create_user("api-leitor")
        u.user_permissions.add(Permission.objects.get(content_type__app_label="inventario", codename="view_ativo"))
        self.autenticar(u)
        self.assertEqual(self.client.get("/api/v1/ativos/").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/ativos/", {"ordenar": "-risco"}).status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/vulnerabilidades/{self.v.pk}/ativos/").status_code, 403)

    def test_ativos_afetados_por_vulnerabilidade(self):
        resposta = self.client.get(f"/api/v1/vulnerabilidades/{self.v.pk}/ativos/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["resultados"][0]["ativo_id"], self.a.pk)
        self.assertEqual(self.client.get("/api/v1/vulnerabilidades/NAO-EXISTE/ativos/").status_code, 404)
        self.assertEqual(self.client.post("/api/v1/ativos/").status_code, 405)

    def test_busca_maliciosa_e_tratada_como_texto(self):
        resposta = self.client.get("/api/v1/ativos/", {"busca": "' OR 1=1 --"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["total"], 0)
        self.assertEqual(self.client.get("/api/v1/ativos/").json()["total"], 2)

    def test_carregamento_antecipado_remove_consultas_n_mais_1(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from inventario.models import Ativo

        with CaptureQueriesContext(connection) as lento:
            nomes = [ativo.sala.nome for ativo in Ativo.objects.order_by("pk")]
        with CaptureQueriesContext(connection) as rapido:
            nomes_antecipados = [ativo.sala.nome for ativo in Ativo.objects.select_related("sala").order_by("pk")]
        self.assertEqual(nomes, nomes_antecipados)
        self.assertEqual(len(lento), 3)
        self.assertEqual(len(rapido), 1)

    def test_documentacao_interativa_e_especificacao_locais(self):
        pagina = self.client.get("/api/v1/docs/")
        self.assertContains(pagina, "Consultar a API v1")
        self.assertContains(pagina, "/api/v1/ativos/")
        contrato = self.client.get("/api/v1/openapi.json")
        self.assertEqual(contrato.status_code, 200)
        self.assertEqual(contrato.json()["openapi"], "3.1.0")
        self.client.logout()
        self.assertEqual(self.client.get("/api/v1/openapi.json").status_code, 401)
