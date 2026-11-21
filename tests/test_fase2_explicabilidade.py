from unittest import TestCase

from inventario.dominio.vulnerabilidades import Dependencia, Incidencia, Vulnerabilidade
from inventario.matematica.risco import ModeloRisco
from .base import BancoTeste


class ExplicacaoCalculo(TestCase):
    def test_explicacao_deriva_do_mesmo_calculo_e_da_simulacao(self):
        vul = Vulnerabilidade("VUL-RCE-0001", "Exemplo", "RCE", 8)
        modelo = ModeloRisco(["A", "B"], [vul], [Incidencia("INC-1", "A", vul.id)],
                             [Dependencia("B", "A", 0.25)], {"A": 2, "B": 1}, {vul.id})
        for perfil in ("puro", "operacional"):
            with self.subTest(perfil=perfil):
                item = modelo.calcular(perfil=perfil, explicar=True).prioridade_correcao[0]
                explicacao = item["explicacao"]
                self.assertAlmostEqual(explicacao["reducao_direta"] + explicacao["reducao_propagada"], item["reducao_total_estimada"])
                self.assertAlmostEqual(sum(i["contribuicao"] for i in explicacao["ativos_diretos"]), explicacao["reducao_direta"])
                self.assertEqual(explicacao["ativos_diretos"][0]["fator_exposicao"], 2 if perfil == "operacional" else 1)
                self.assertAlmostEqual(item["reducao_total_estimada"], modelo.simular(["INC-1"], perfil=perfil)["ganho_total"])
                self.assertEqual(explicacao["kev_aplicado"], perfil == "operacional")
                self.assertIn("epss", explicacao["nao_utilizados"])


class ExplicacaoWeb(BancoTeste):
    def test_api_e_tela_exibem_mesmos_componentes(self):
        resposta = self.client.get("/api/risco/?perfil=operacional")
        self.assertEqual(resposta.status_code, 200)
        item = next(i for i in resposta.json()["prioridade_correcao"] if i["vulnerabilidade_id"] == self.v.pk)
        self.assertTrue(item["explicacao"]["kev_aplicado"])
        self.assertEqual(item["explicacao"]["reducao_total"], item["reducao_total_estimada"])
        self.assertContains(self.client.get("/prioridades/?perfil=operacional"), "EPSS, SSVC e criticidade do serviço não entram")

    def test_snapshots_antigos_nao_inventam_historico_e_novos_sao_comparados(self):
        from inventario.aplicacao.mudancas_risco import mudancas
        from inventario.aplicacao.risco import gravar_snapshot_risco
        from inventario.models import SnapshotRisco

        antigo = SnapshotRisco.objects.create(chave="antigo", risco_total=4, perfil="puro", por_ativo={})
        self.assertFalse(mudancas()["disponivel"])
        primeiro = gravar_snapshot_risco()
        parcial = mudancas()
        self.assertTrue(parcial["disponivel"])
        self.assertIsNone(parcial["top"])
        self.assertIsNone(parcial["mttr"])
        self.assertIsNotNone(primeiro.detalhes)
        self.i.delete()
        segundo = gravar_snapshot_risco()
        comparacao = mudancas()
        self.assertEqual(comparacao["top"]["sairam"], [self.v.pk])
        self.assertAlmostEqual(comparacao["variacao_risco"], segundo.risco_total - primeiro.risco_total)
        self.assertIn("correcoes", comparacao["mttr"]["atual"])
        resposta = self.client.get("/api/v1/risco/mudancas/")
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta["Cache-Control"], "no-store")
        self.assertContains(self.client.get("/"), "Mudanças entre os últimos registros")
        antigo.delete()

    def test_api_nega_sem_permissao_historico(self):
        from django.contrib.auth import get_user_model
        usuario = get_user_model().objects.create_user("sem-historico")
        self.autenticar(usuario)
        self.assertEqual(self.client.get("/api/v1/risco/mudancas/").status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get("/api/v1/risco/mudancas/").status_code, 401)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get("/api/v1/risco/mudancas/").status_code, 403)
