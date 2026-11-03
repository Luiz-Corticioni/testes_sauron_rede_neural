import json
from pathlib import Path
import time
from unittest.mock import patch
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client
from inventario.infraestrutura.cve_client import IntegracaoCVEError, TTL
from inventario.infraestrutura.arquivos import salvar_json_atomico
from inventario.dominio.comparacao_cvss import comparar_notas
from inventario.models import Vulnerabilidade, Software
from inventario.aplicacao.operacao_cves import registrar_sugestao
from .base import BancoTeste
from .test_comparacao_cvss import registro, V31


class ComparacaoWeb(BancoTeste):
    @patch("inventario.infraestrutura.cve_client._baixar_json")
    def test_post_consulta_compara_e_preserva_cadastros(self, baixar):
        baixar.return_value = {"vulnerabilities": [{"cve": registro()}]}
        antes = Vulnerabilidade.objects.count()
        r = self.client.post("/comparar-cvss/", {"cve": "CVE-2024-12345", "atualizar": "on"})
        self.assertEqual(r.status_code, 200)
        resultado = r.context["resultado"]
        self.assertEqual(resultado["local31"]["nota"], 9.8)
        self.assertEqual(resultado["diferenca_40_menos_31"], -0.5)
        self.assertEqual(resultado["consulta"]["origem"], "NVD pela internet")
        self.assertTrue(resultado["consulta"]["consultado_em"])
        self.assertContains(r, "security@example.org")
        self.assertEqual(Vulnerabilidade.objects.count(), antes)
        baixar.assert_called_once()

    @patch(
        "inventario.infraestrutura.cve_client._baixar_json", side_effect=AssertionError("Sem rede")
    )
    def test_get_e_calculo_local_nao_acessam_rede(self, baixar):
        r = self.client.get("/comparar-cvss/", {"vulnerabilidade": self.v.pk})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context["resultado"])
        r = self.client.post("/comparar-cvss/", {"vetor": V31})
        self.assertEqual(r.context["resultado"]["local31"]["nota"], 9.8)
        self.assertIsNone(r.context["resultado"]["diferenca_40_menos_31"])
        self.assertContains(r, "Não disponível")
        baixar.assert_not_called()

    @patch(
        "inventario.infraestrutura.cve_client._baixar_json",
        side_effect=IntegracaoCVEError("Rede indisponível"),
    )
    def test_falha_de_rede_mostra_cache_expirado_com_data(self, baixar):
        salvar_json_atomico(
            settings.DATA_DIR / "cache" / "nvd" / "CVE-2024-12345.json",
            {"ts": time.time() - TTL - 30, "cve": registro()},
        )
        r = self.client.post("/comparar-cvss/", {"cve": "CVE-2024-12345", "atualizar": "on"})
        self.assertEqual(r.status_code, 200)
        resultado = r.context["resultado"]
        self.assertEqual(resultado["consulta"]["origem"], "cache NVD")
        self.assertTrue(resultado["consulta"]["expirado"])
        self.assertContains(r, "Cache NVD expirado")
        self.assertEqual(resultado["nvd40"]["nota"], 9.3)

    @patch("inventario.infraestrutura.cve_client._baixar_json")
    def test_entrada_invalida_e_cve_diferente_do_cadastro_nao_consultam(self, baixar):
        for dados in (
            {},
            {"cve": "../../passwd", "atualizar": "on"},
            {"cve": "CVE-2024-12345", "vetor": "CVSS:4.0/AV:N", "atualizar": "on"},
            {"vulnerabilidade": self.v.pk, "cve": "CVE-2024-12345", "atualizar": "on"},
        ):
            r = self.client.post("/comparar-cvss/", dados)
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.context["form"].errors)
            self.assertIsNone(r.context["resultado"])
        baixar.assert_not_called()

    @patch("inventario.infraestrutura.cve_client._baixar_json")
    def test_consulta_exige_login_permissao_e_csrf(self, baixar):
        self.client.logout()
        self.assertEqual(
            self.client.post(
                "/comparar-cvss/", {"cve": "CVE-2024-12345", "atualizar": "on"}
            ).status_code,
            302,
        )
        sem = get_user_model().objects.create_user("sem-comparacao")
        self.autenticar(sem)
        self.assertEqual(self.client.get("/comparar-cvss/").status_code, 403)
        cliente = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, cliente)
        self.assertEqual(
            cliente.post(
                "/comparar-cvss/", {"cve": "CVE-2024-12345", "atualizar": "on"}
            ).status_code,
            403,
        )
        baixar.assert_not_called()

    def test_4_ausente_e_zero_permanecem_distintos_no_html(self):
        c = registro()
        c["metrics"].pop("cvssMetricV40")
        salvar_json_atomico(
            settings.DATA_DIR / "cache" / "nvd" / "CVE-2024-12345.json",
            {"ts": time.time(), "cve": c},
        )
        r = self.client.post("/comparar-cvss/", {"cve": c["id"]})
        self.assertIsNone(r.context["resultado"]["nvd40"]["nota"])
        self.assertContains(r, "Não disponível")
        self.assertContains(r, "Não calculada")

    def test_fixture_publica_e_mesma_selecao_no_cadastro_por_cpe(self):
        c = json.loads(
            Path(__file__)
            .with_name("fixtures")
            .joinpath("nvd_cvss_duas_versoes.json")
            .read_text(encoding="utf-8")
        )["cve"]
        r = comparar_notas(c)
        self.assertEqual(r["local31"]["nota"], 8.8)
        self.assertEqual(r["nvd40"]["nota"], 8.7)
        self.assertEqual(r["diferenca_40_menos_31"], -0.1)
        self.assertEqual(r["nvd40"]["publicador"], "nvd@nist.gov")
        s = Software.objects.create(ativo=self.a, nome="Produto", fornecedor="Exemplo", versao="1")
        self.assertTrue(registrar_sugestao(s, c))
        v = Vulnerabilidade.objects.get(cve_id=c["id"])
        self.assertEqual(v.cvss, 8.8)
        self.assertEqual(v.cvss_v4["baseScore"], 8.7)
        self.assertEqual(v.cvss_v4["fonte"], "nvd@nist.gov")

    def test_guia_e_ajuda_contextual_explicam_conceitos(self):
        r = self.client.get("/guia/")
        self.assertEqual(r.status_code, 200)
        for palavra in ("CISA", "EPSS", "MTTR", "probabilidade"):
            self.assertIn(palavra, r.content.decode())
        r = self.client.get("/matrizes/")
        self.assertContains(r, "Como ler M, A e x")

    def test_nota_legada_divergente_aparece_no_comparador_sem_ser_alterada(self):
        Vulnerabilidade.objects.filter(pk=self.v.pk).update(cvss=7.5)
        r = self.client.post(
            "/comparar-cvss/",
            {"vulnerabilidade": self.v.pk, "cve": self.v.cve_id, "vetor": self.v.cvss_vetor},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "A nota cadastrada difere")
        self.assertEqual(r.context["resultado"]["local31"]["nota"], 10.0)
        self.v.refresh_from_db()
        self.assertEqual(self.v.cvss, 7.5)

    @patch(
        "inventario.infraestrutura.cve_client._baixar_json", side_effect=AssertionError("Sem rede")
    )
    def test_terminal_compara_pelo_mesmo_servico_sem_rede_implicita(self, baixar):
        from inventario.cli_menus.cves import CvesMenu
        from unittest.mock import Mock

        salvar_json_atomico(
            settings.DATA_DIR / "cache" / "nvd" / "CVE-2024-12345.json",
            {"ts": time.time(), "cve": registro()},
        )
        menu = CvesMenu()
        menu._texto = Mock(side_effect=["CVE-2024-12345", ""])
        menu._confirmar = Mock(return_value=False)
        menu._tabela = Mock()
        menu.saida = Mock()
        menu.comparar_cvss_terminal()
        self.assertEqual(menu._tabela.call_args.args[1][2][1], 9.3)
        self.assertIn("-0.5", " ".join(str(c.args[0]) for c in menu.saida.call_args_list))
        baixar.assert_not_called()
