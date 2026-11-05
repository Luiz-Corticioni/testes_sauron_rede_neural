from datetime import timedelta
import json
import time
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import Client
from django.utils import timezone
from inventario.aplicacao.autorizacao import exigir, sessao_interativa
from inventario.aplicacao.cadastros import salvar_cadastro, remover_cadastro
from inventario.aplicacao.operacao import alterar_status
from inventario.aplicacao.ssvc import registrar_avaliacao, contexto_atual
from inventario.aplicacao.montecarlo import calcular_montecarlo
from inventario.models import Software, AvaliacaoSSVC, ObservacaoEPSS, Vulnerabilidade, RegistroAuditoria
from .base import BancoTeste


class SegurancaConsolidada(BancoTeste):
    def usuario_com(self, *codigos):
        u = get_user_model().objects.create_user("operador-teste", password="senha-teste-123")
        u.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario", codename__in=codigos))
        return u

    def test_cache_de_permissao_revogada_nao_autoriza_servico(self):
        u = self.usuario_com("change_incidencia")
        self.assertTrue(u.has_perm("inventario.change_incidencia"))
        u.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            exigir(u, "inventario.change_incidencia")

    def test_concessao_recente_nao_reutiliza_cache_negativo(self):
        u = self.usuario_com()
        self.assertFalse(u.has_perm("inventario.view_ativo"))
        u.user_permissions.add(Permission.objects.get(codename="view_ativo"))
        self.assertEqual(exigir(u, "inventario.view_ativo").pk, u.pk)

    def test_conta_desativada_e_papel_de_grupo_revogado_sao_bloqueados(self):
        from django.contrib.auth.models import Group
        u = self.usuario_com()
        grupo = Group.objects.create(name="Teste")
        grupo.permissions.add(Permission.objects.get(codename="change_incidencia"))
        u.groups.add(grupo)
        self.assertTrue(u.has_perm("inventario.change_incidencia"))
        grupo.permissions.clear()
        with self.assertRaises(PermissionDenied):
            alterar_status(self.i.pk, "TRATAMENTO", u)
        get_user_model().objects.filter(pk=self.usuario.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            alterar_status(self.i.pk, "TRATAMENTO", self.usuario)

    def test_revogacao_em_cadastro_edicao_exclusao_nao_modifica_dados(self):
        s = Software.objects.create(ativo=self.a, nome="Teste", versao="1", fornecedor="Equipe")
        for perm, funcao in (("change_software", salvar_cadastro), ("delete_software", remover_cadastro)):
            u = get_user_model().objects.create_user(perm)
            u.user_permissions.add(Permission.objects.get(codename=perm))
            self.assertTrue(u.has_perm("inventario."+perm))
            u.user_permissions.clear()
            s.nome = "Alterado"
            with self.assertRaises(PermissionDenied):
                funcao(s, u)
        s.refresh_from_db()
        self.assertEqual(s.nome, "Teste")

    def test_ssvc_revoga_mesmo_com_usuario_antigo(self):
        u = self.usuario_com("view_incidencia", "view_ativo", "view_vulnerabilidade", "change_incidencia")
        self.assertTrue(u.has_perm("inventario.change_incidencia"))
        u.user_permissions.remove(Permission.objects.get(codename="change_incidencia"))
        with self.assertRaises(PermissionDenied):
            registrar_avaliacao(self.i.pk, u, {}, "Evidência", timezone.localdate()+timedelta(days=1), contexto_atual(self.i)[1], "Patch")
        self.assertFalse(AvaliacaoSSVC.objects.exists())

    def test_aceite_preparado_no_formulario_revalida_permissao_antes_de_salvar(self):
        from inventario.aplicacao.decisoes import preparar_formulario
        u = self.usuario_com("change_incidencia", "add_incidencia", "aceitar_risco")
        anterior = self.i.status
        preparar_formulario(self.i, {"status": "ACEITA", "justificativa": "Termos de teste", "aceita_ate": timezone.localdate()+timedelta(days=10)}, u)
        self.assertTrue(self.i._decisao_preparada)
        u.user_permissions.remove(Permission.objects.get(codename="aceitar_risco"))
        with self.assertRaises(PermissionDenied):
            salvar_cadastro(self.i, u)
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, anterior)

    def test_aprovador_em_cache_nao_preserva_permissao_revogada(self):
        from inventario.aplicacao.decisoes import validar_segundo
        u = self.usuario_com("change_incidencia")
        self.i.aprovada_por = u
        self.assertTrue(self.i.aprovada_por.has_perm("inventario.change_incidencia"))
        u.user_permissions.clear()
        with self.assertRaises(ValidationError):
            validar_segundo(self.i, "inventario.change_incidencia", self.usuario.pk)

    def cli(self):
        from inventario.cli import SauronCLI
        from django_otp.plugins.otp_totp.models import TOTPDevice
        cli = SauronCLI(entrada=lambda _: "", saida=lambda _: None)
        cli.usuario = self.usuario
        cli._inicio_cli = cli._ultima_cli = cli._reauth_cli = time.monotonic()
        cli._mfa_cli_id = TOTPDevice.objects.get(user=self.usuario).persistent_id
        return cli

    def test_pausa_longa_no_cli_bloqueia_gravacao_sem_pedir_senha_dentro_da_transacao(self):
        cli = self.cli()
        cli._reauth_cli -= 100000
        obj = Software(ativo=self.a, nome="Teste", versao="1", fornecedor="Equipe")
        with patch("inventario.cli.getpass", side_effect=AssertionError("Não pedir senha aqui")), sessao_interativa(cli), self.assertRaises(PermissionDenied):
            salvar_cadastro(obj, cli.usuario)
        self.assertFalse(Software.objects.exists())

    def test_dispositivo_mfa_revogado_durante_preenchimento_impede_gravacao(self):
        from django_otp.plugins.otp_totp.models import TOTPDevice
        cli = self.cli()
        TOTPDevice.objects.filter(user=self.usuario).delete()
        with sessao_interativa(cli), self.assertRaises(PermissionDenied):
            alterar_status(self.i.pk, "TRATAMENTO", self.usuario)
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, "ABERTA")

    def test_exportacao_revalida_sessao_apos_confirmar_sobrescrita(self):
        from django.conf import settings
        cli = self.cli()
        destino = settings.DATA_DIR / "ativos_sauron.csv"
        destino.write_text("arquivo anterior", encoding="utf-8")
        def confirmar(_):
            cli._ultima_cli -= 100000
            return True
        with patch.object(cli, "_confirmar", side_effect=confirmar), patch.object(cli, "login", side_effect=AssertionError("Não abrir login aqui")):
            cli.exportar_csv()
        self.assertEqual(destino.read_text(encoding="utf-8"), "arquivo anterior")

    def test_contexto_cli_nao_vaza_para_chamadas_fora_da_sessao(self):
        cli = self.cli()
        cli._reauth_cli -= 100000
        with sessao_interativa(cli), self.assertRaises(PermissionDenied):
            exigir(self.usuario, "inventario.change_incidencia")
        self.assertEqual(exigir(self.usuario, "inventario.change_incidencia").pk, self.usuario.pk)

    def test_csv_permissao_revogada_durante_validacao_nao_grava(self):
        from inventario.infraestrutura.importacao import importar_csv
        u = self.usuario_com("add_ativo")
        def validar(_):
            u.user_permissions.clear()
            return [], []
        with patch("inventario.infraestrutura.importacao.ler_linhas", return_value=[]), patch("inventario.infraestrutura.importacao.validar_lote", side_effect=validar), self.assertRaises(PermissionDenied):
            importar_csv("dados", u, dry_run=False)

    def test_epss_revogacao_durante_rede_impede_gravacao(self):
        from inventario.aplicacao.epss import sincronizar_epss
        u = self.usuario_com("view_vulnerabilidade", "change_vulnerabilidade")
        def buscar(_):
            u.user_permissions.clear()
            return {self.v.cve_id: {"epss": .2, "percentil": .5, "modelo": "teste", "data": timezone.now().date().isoformat()}}
        with patch("inventario.aplicacao.epss.EpssClient.buscar", side_effect=buscar), self.assertRaises(PermissionDenied):
            sincronizar_epss(usuario=u, limite=50)
        self.assertFalse(ObservacaoEPSS.objects.exists())


class HorizonteEOrientacao(BancoTeste):
    def epss(self, v, valor=.1, dias=0):
        o = ObservacaoEPSS.objects.create(cve_id=v.cve_id, data=timezone.now().date()-timedelta(days=dias), epss=valor,
            percentil=.5, modelo="fixture", assinatura=f"{v.pk}-{dias}-{valor}".ljust(64,"0"))
        v.epss, v.epss_data, v.epss_observacao = valor, o.data, o
        v.save()

    def preparar(self, dias=0):
        self.w.cve_id = "CVE-2024-0002"
        self.w.save()
        self.epss(self.v, dias=dias)
        self.epss(self.w, dias=dias)

    def calcular(self, **kw):
        return calcular_montecarlo({"n": 500, "custos": {"C": 100, "I": 20, "A": 30}, **kw})

    def test_sem_dados_retorna_pendencias_em_vez_de_zero(self):
        r = self.calcular()
        self.assertFalse(r["disponivel"])
        self.assertIsNone(r["antes"])
        self.assertEqual(r["pendencias_total"], 2)

    def test_ep_ss_recente_retornam_30_dias_sem_campos_anuais(self):
        self.preparar()
        r = self.calcular()
        self.assertTrue(r["disponivel"])
        self.assertEqual(r["horizonte_dias"], 30)
        self.assertEqual(r["entradas"][0]["probabilidade_cenario_30d"], .1)
        self.assertFalse({"ALE", "mensal", "ganho_ALE"} & set(r))
        self.assertNotIn("ALE", r["antes"])

    def test_dado_vencido_ou_divergente_fica_indisponivel(self):
        self.preparar(dias=3)
        self.assertFalse(self.calcular()["disponivel"])
        self.epss(self.v)
        self.epss(self.w)
        Vulnerabilidade.objects.filter(pk=self.v.pk).update(epss=.9)
        self.assertFalse(self.calcular()["disponivel"])

    def test_cache_nao_esconde_vencimento_de_ep_ss_no_dia_seguinte(self):
        self.preparar(dias=2)
        self.assertTrue(self.calcular()["disponivel"])
        amanha = timezone.now()+timedelta(days=1)
        with patch("inventario.aplicacao.montecarlo.timezone.now", return_value=amanha):
            self.assertFalse(self.calcular()["disponivel"])

    def test_api_rejeita_piso_kev_e_horizonte_antigo(self):
        for dados in ({"piso_kev": .2}, {"horizonte_dias": 365}):
            r = self.client.post("/api/montecarlo/", json.dumps(dados), content_type="application/json")
            self.assertEqual(r.status_code, 400)

    def test_limite_global_de_simulacoes_devolve_429_e_libera_vagas(self):
        from inventario.infraestrutura.limite_simulacoes import vaga_simulacao
        self.preparar()
        with vaga_simulacao(), vaga_simulacao():
            resposta = self.client.post('/api/montecarlo/', json.dumps({'n': 100}), content_type='application/json')
            self.assertEqual(resposta.status_code, 429)
            self.assertEqual(resposta['Retry-After'], '3')
        resposta = self.client.post('/api/montecarlo/', json.dumps({'n': 100}), content_type='application/json')
        self.assertEqual(resposta.status_code, 200)
        self.assertTrue(resposta.json()['disponivel'])

    def test_vaga_de_simulacao_e_liberada_ao_ocorrer_excecao(self):
        from inventario.infraestrutura.limite_simulacoes import vaga_simulacao
        with self.assertRaises(RuntimeError):
            with vaga_simulacao():
                raise RuntimeError('Falha sintética')
        with vaga_simulacao(), vaga_simulacao():
            pass

    def test_vazio_legitimo_zero_com_escopo_explicito(self):
        self.a.status = self.b.status = "INATIVO"
        self.a.save()
        self.b.save()
        r = self.calcular()
        self.assertTrue(r["disponivel"])
        self.assertEqual(r["quantidade_incidencias"], 0)
        self.assertEqual(r["antes"]["media"], 0)

    def test_30_dias_conserva_probabilidade_em_vez_de_anualizar(self):
        from inventario.matematica.montecarlo import simular
        r = simular([{"ativo": "A", "cve": "CVE", "cvss": 10, "epss": .1, "vetor": "CVSS:3.1/C:H/I:H/A:H"}],
                    custos={"C": 100, "I": 20, "A": 30}, n=50000)
        self.assertAlmostEqual(r["antes"]["probabilidade_perda"], .1, delta=.01)
        self.assertAlmostEqual(r["antes"]["media"], 15, delta=1)

    def test_atualizacao_epss_exige_post_csrf_e_permissao_especifica(self):
        c = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, c)
        self.assertEqual(self.client.get("/epss/atualizar/").status_code, 405)
        self.assertEqual(c.post("/epss/atualizar/", {}).status_code, 403)
        u = get_user_model().objects.create_user("somente-leitura")
        u.user_permissions.set(Permission.objects.filter(codename__startswith="view_"))
        self.autenticar(u)
        with patch("inventario.aplicacao.epss.EpssClient.buscar") as rede:
            self.assertEqual(self.client.post("/epss/atualizar/", {}).status_code, 403)
            rede.assert_not_called()

    def test_botao_epss_real_atualiza_e_audita_ator(self):
        payload = {"data": [{"cve": self.v.cve_id, "epss": ".2", "percentile": ".9", "date": timezone.now().date().isoformat()}]}
        with patch("inventario.infraestrutura.cve_client._baixar_json", return_value=payload):
            r = self.client.post("/epss/atualizar/", {})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/montecarlo/")
        self.v.refresh_from_db()
        self.assertEqual(self.v.epss, .2)
        self.assertEqual(RegistroAuditoria.objects.get(acao="EPSS_SINCRONIZADO").usuario_id, self.usuario.pk)

    def test_ajudas_e_exemplos_presentes_nas_telas_principais(self):
        for url in ("/", "/incidencias/", "/documentos/", "/grafo-relacoes/", "/qualidade-relacoes/", "/modo-euler/", "/montecarlo/", f"/incidencias/{self.i.pk}/ssvc/"):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertContains(r, "Como usar esta tela")
            self.assertContains(r, "Próximo passo:")
        r = self.client.get("/guia/")
        self.assertContains(r, "Para o responsável pelo negócio")
        self.assertContains(r, "Para o analista de segurança")
        self.assertContains(r, "Para quem mantém o inventário")

    def test_interface_nao_promete_ano_nem_usa_sigla_ale(self):
        r = self.client.get("/montecarlo/")
        self.assertContains(r, "30 dias")
        self.assertNotContains(r, "12 meses")
        self.assertNotContains(r, "Piso anual")
        self.assertContains(r, "não é um modelo FAIR completo")
