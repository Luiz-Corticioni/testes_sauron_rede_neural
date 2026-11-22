from unittest import TestCase
from inventario.dominio.qualidade_dados import avaliar, componente
from .base import BancoTeste


class IndiceQualidade(TestCase):
    def test_media_explicita_sem_converter_indeterminado_em_zero(self):
        epss = componente("epss", "EPSS", 1, 2, "observações locais")
        revisoes = componente("revisoes", "Revisões", 1, 1, "perímetro declarado")
        resultado = avaliar([epss, revisoes])
        self.assertEqual(resultado["score"], 75.0)
        self.assertEqual([c["percentual"] for c in resultado["componentes"]], [50, 100])
        desconhecido = componente("premissas", "Premissas", None, None, "não verificadas")
        self.assertIsNone(avaliar([epss, desconhecido])["score"])

    def test_entrada_invalida_e_indice_sem_denominador_sao_rejeitados(self):
        for dados in ((2, 1), (-1, 1), (0, 0), (None, 1), (True, 1)):
            with self.subTest(dados=dados), self.assertRaises(ValueError):
                componente("x", "X", *dados, "origem")
        item = componente("x", "X", 1, 1, "origem")
        with self.assertRaises(ValueError):
            avaliar([item, item])


class QualidadeAplicacao(BancoTeste):
    def test_cve_vazia_nao_conta_como_evidencia_epss(self):
        from django.utils import timezone
        from inventario.aplicacao.qualidade_dados import qualidade_ativo
        from inventario.models import ObservacaoEPSS

        data = timezone.now().date()
        observacao = ObservacaoEPSS.objects.create(cve_id="", data=data, epss=0.2,
                                                  percentil=0.5, assinatura="b" * 64)
        self.v.cve_id, self.v.epss, self.v.epss_data, self.v.epss_observacao = "", 0.2, data, observacao
        self.v.save()
        resultado = qualidade_ativo(self.usuario, self.a.pk)
        self.assertEqual(resultado["componentes"][0]["percentual"], 0)

    def test_ativo_exige_contexto_e_usa_epSs_coerente_e_revisao_real(self):
        from datetime import timedelta
        from django.utils import timezone
        from inventario.aplicacao.cobertura import salvar_perimetro, preparar_revisao, registrar_revisao
        from inventario.aplicacao.qualidade_dados import qualidade_ativo
        from inventario.models import ObservacaoEPSS, RegistroAuditoria

        data = timezone.now().date()
        observacao = ObservacaoEPSS.objects.create(cve_id=self.v.cve_id, data=data, epss=0.2,
                                                  percentil=0.5, assinatura="a" * 64)
        self.v.epss, self.v.epss_data, self.v.epss_observacao = 0.2, data, observacao
        self.v.save()
        sem_contexto = qualidade_ativo(self.usuario, self.a.pk)
        self.assertIsNone(sem_contexto["score"])
        self.assertEqual(sem_contexto["componentes"][0]["percentual"], 100)
        p = salvar_perimetro(self.usuario, "qualidade", "Perímetro fictício", [self.a.pk])
        _, resumo = preparar_revisao(self.usuario, p.pk, "REDE", self.a.pk)
        data_revisao = timezone.localdate()
        registrar_revisao(self.usuario, p.pk, "REDE", self.a.pk, "", "SEM_RELACOES", "Revisão fictícia",
                          data_revisao, data_revisao + timedelta(days=10), resumo["sha256"])
        antes = RegistroAuditoria.objects.count()
        resultado = qualidade_ativo(self.usuario, self.a.pk, p.pk)
        self.assertEqual(resultado["score"], 66.67)
        self.assertEqual(RegistroAuditoria.objects.count(), antes)
        self.assertIn("não mede segurança", resultado["aviso"])
        api = self.client.get(f"/api/v1/qualidade/ativos/{self.a.pk}/", {"perimetro": p.pk, "tipo": "REDE"})
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api.json()["score"], resultado["score"])
        pagina = self.client.get(f"/ativos/{self.a.pk}/", {"qualidade_perimetro": p.pk, "qualidade_tipo": "REDE"})
        self.assertContains(pagina, "Qualidade das evidências")
        self.assertEqual(pagina.context["qualidade"]["score"], 66.67)

    def test_financeiro_e_acesso_negado_nao_fabricam_dados(self):
        from django.contrib.auth import get_user_model
        from django.core.exceptions import PermissionDenied
        from inventario.aplicacao.qualidade_dados import qualidade_ativo, qualidade_montecarlo

        self.assertIsNone(qualidade_montecarlo(4, 1)["score"])
        self.assertEqual(qualidade_montecarlo(4, 1)["componentes"][0]["percentual"], 75)
        self.assertIsNone(qualidade_montecarlo(0, 0)["componentes"][0]["percentual"])
        usuario = get_user_model().objects.create_user("sem-qualidade")
        with self.assertRaises(PermissionDenied):
            qualidade_ativo(usuario, self.a.pk)
        self.autenticar(usuario)
        self.assertEqual(self.client.get(f"/api/v1/qualidade/ativos/{self.a.pk}/").status_code, 403)
        self.assertNotContains(self.client.get(f"/ativos/{self.a.pk}/"), "Qualidade das evidências", status_code=403)

    def test_servico_sem_ativos_tem_qualidade_indeterminada(self):
        from inventario.aplicacao.cobertura import salvar_perimetro
        from inventario.aplicacao.qualidade_dados import qualidade_servico
        from inventario.aplicacao.servicos_negocio import salvar_servico

        perimetro = salvar_perimetro(self.usuario, "vazio", "Perímetro sem ativos", [])
        servico = salvar_servico(self.usuario, {"nome": "Serviço fictício", "descricao": "Teste",
            "responsavel": "Equipe", "impacto_interrupcao": "Não medido", "criticidade": 2,
            "objetivo_recuperacao_horas": None, "perimetro": perimetro})
        resultado = qualidade_servico(self.usuario, servico.pk)
        self.assertIsNone(resultado["score"])
        self.assertIsNone(resultado["componentes"][0]["percentual"])
        self.assertIsNone(resultado["componentes"][1]["percentual"])
        self.assertIsNone(self.client.get(f"/api/v1/qualidade/servicos/{servico.pk}/").json()["score"])
        self.assertContains(self.client.get(f"/servicos-negocio/{servico.pk}/"), "indisponível")

    def test_amostra_incompleta_nao_e_convertida_em_cobertura_zero(self):
        from unittest.mock import patch
        from inventario.aplicacao.qualidade_dados import componente_fontes

        fonte_parcial = {"nvd": {"resumo": {"codigo": "incompleto"}},
                         "kev": {"resumo": {"codigo": "ok"}}}
        with patch("inventario.aplicacao.estado_fontes.resumo_fontes", return_value=fonte_parcial):
            resultado = componente_fontes()
        self.assertIsNone(resultado["percentual"])
        self.assertIsNone(resultado["validos"])
        self.assertIn("incompleta", resultado["motivo"])

    def test_api_rejeita_contexto_invalido_e_exige_sessao(self):
        self.assertEqual(self.client.get(f"/api/v1/qualidade/ativos/{self.a.pk}/", {"perimetro": "-1"}).status_code, 422)
        self.assertEqual(self.client.get(f"/api/v1/qualidade/ativos/{self.a.pk}/", {"tipo": "OUTRO"}).status_code, 422)
        self.assertEqual(self.client.get("/api/v1/qualidade/ativos/NAOEXISTE/").status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(f"/api/v1/qualidade/ativos/{self.a.pk}/").status_code, 401)

    def test_prioridades_nao_exibe_zero_quando_calculo_falha(self):
        from unittest.mock import patch
        with patch("inventario.web.views_visualizacoes.calcular_risco_banco", side_effect=ValueError("falha simulada")):
            pagina = self.client.get("/prioridades/")
        self.assertContains(pagina, "Indisponível")
        self.assertNotContains(pagina, 'data-global-index>0')
