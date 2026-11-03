
from unittest.mock import patch
from django.test import override_settings
from inventario.aplicacao.operacao_cves import registrar_sugestao, sugerir_cves
from inventario.aplicacao.cadastros import proximo_id_vulnerabilidade
from inventario.models import Software, Vulnerabilidade
from .base import BancoTeste


def cve(n=1, score=8.2, status="Analyzed", publicada="2026-01-01"):
    return {"id": f"CVE-2026-{n:04}", "vulnStatus":status, "published":publicada,
            "metrics":{"cvssMetricV40":[{"cvssData":{"baseScore":score, "vectorString":"CVSS:4.0/AV:N", "version":"4.0"}}]}}


class R10(BancoTeste):
    def setUp(self):
        super().setUp()
        self.s = Software.objects.create(ativo=self.a, nome="teste", fornecedor="teste", versao="1",
                                         cpe23="cpe:2.3:a:teste:teste:1:*:*:*:*:*:*:*")

    def test_rejected_e_awaiting_e_v4(self):
        self.assertFalse(registrar_sugestao(self.s, cve(status="Rejected")))
        self.assertTrue(registrar_sugestao(self.s, cve(status="Awaiting Analysis")))
        v = Vulnerabilidade.objects.get(cve_id="CVE-2026-0001")
        self.assertEqual(v.cvss_v4["baseScore"], 8.2)
        self.assertEqual(v.cvss, 8.2)
        self.assertEqual(v.confianca_nvd, "BAIXA")

    @override_settings(NVD_MAX_SUGESTOES_CPE=2)
    @patch("inventario.infraestrutura.cve_client.NvdClient.consultar_cpe")
    def test_filtra_antigas_e_limita_por_cpe(self, consultar):
        consultar.return_value = {"cves":[cve(1, 2, publicada="2000-01-01"),
            cve(2, 8), cve(3, 9), cve(4, 7)], "total":4, "truncado":False}
        self.assertEqual(sugerir_cves()["sugeridas"], 2)
        self.assertFalse(Vulnerabilidade.objects.filter(cve_id="CVE-2026-0001").exists())

    def test_id_maximo_sem_teto_uma_consulta(self):
        Vulnerabilidade.objects.create(id="VUL-OUTRA-10000", descricao="limite", cvss=1)
        with self.assertNumQueries(1):
            self.assertEqual(proximo_id_vulnerabilidade("OUTRA"), "VUL-OUTRA-10001")

    @patch("inventario.infraestrutura.cve_client.time.sleep")
    @patch("inventario.infraestrutura.cve_client._baixar_json")
    def test_retry_limitacao_remota(self, baixar, dormir):
        from inventario.infraestrutura.cve_client import NvdClient, FonteLimitada
        from django.conf import settings
        baixar.side_effect = [FonteLimitada(1), {"vulnerabilities":[{"cve":cve()}]}]
        self.assertEqual(NvdClient(cache_dir=settings.DATA_DIR/"nvd").atualizar("CVE-2026-0001")["id"], "CVE-2026-0001")
        self.assertEqual(baixar.call_count, 2)
        dormir.assert_called()


    @patch("inventario.infraestrutura.cve_client.time.sleep")
    @patch("inventario.infraestrutura.cve_client.time.time", side_effect=[1,1,1,1,1,1,32])
    def test_sexta_requisicao_espera_janela_local(self, relogio, dormir):
        from inventario.infraestrutura.cve_client import NvdClient
        from django.conf import settings
        cliente=NvdClient(cache_dir=settings.DATA_DIR/"limite-local")
        for _ in range(6):
            cliente.reservar_requisicao()
        dormir.assert_called_once()
