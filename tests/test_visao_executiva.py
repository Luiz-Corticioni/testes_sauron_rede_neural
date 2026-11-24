from datetime import timedelta
import hashlib
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import Client
from django.utils import timezone

from inventario.aplicacao.fair import criar, executar
from inventario.aplicacao.visao_executiva import LEITURA, exportar, montar
from inventario.models import CenarioFAIR, MembroPerimetro, PerimetroRelacoes, RegistroAuditoria, ServicoNegocio, SnapshotRisco
from .base import BancoTeste
from .test_fair_fluxo import exemplo


class VisaoExecutiva(BancoTeste):
    def test_vazio_nao_inventa_resultado_e_a_tela_responde(self):
        resultado = montar(self.usuario)
        self.assertIsNone(resultado["financeiro"])
        self.assertIsNone(resultado["mudanca"])
        resposta = self.client.get("/executivo/")
        self.assertContains(resposta, "não há execução financeira")
        self.assertContains(resposta, "não é certificação")
        self.assertEqual(resposta["Cache-Control"], "no-store")

    def criar_cenario(self):
        cenario = CenarioFAIR(nome="Cenário fictício", ativo=self.a, evento="Interrupção", ameaca="Falha",
            efeito="A", escopo="Empresa fictícia", origem_frequencia="Estimativa", origem_perdas="Hipótese",
            qualidade="SIMULADO", data_referencia=timezone.localdate(), premissas=exemplo() | {"slef": [1., 1., 1.]})
        cenario = criar(cenario, self.usuario, True)
        return executar(cenario, self.usuario, n=100, seed=42, guardar=True)[1]

    def test_servico_financeiro_snapshot_e_exportacao_auditada(self):
        p = PerimetroRelacoes.objects.create(nome="escopo", descricao="Teste", criada_por=self.usuario, atualizada_por=self.usuario)
        MembroPerimetro.objects.create(perimetro=p, ativo=self.a)
        ServicoNegocio.objects.create(nome="Pedidos", descricao="Serviço", responsavel="Equipe", impacto_interrupcao="Indisponível",
                                      criticidade=4, perimetro=p, criado_por=self.usuario)
        execucao = self.criar_cenario()
        agora = timezone.now()
        SnapshotRisco.objects.create(chave="antigo", perfil="puro", ts=agora-timedelta(days=8), risco_total=10)
        SnapshotRisco.objects.create(chave="atual", perfil="puro", ts=agora-timedelta(days=1), risco_total=15)
        resumo = montar(self.usuario, execucao.pk)
        self.assertEqual(resumo["servicos"][0].pendencias, 1)
        self.assertEqual(resumo["financeiro"]["p95"], execucao.resultado["perda"]["P95"])
        self.assertEqual(resumo["mudanca"]["variacao"], 5)
        resposta = self.client.post("/executivo/exportar/", {"destino": "diretoria", "execucao": execucao.pk})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "não é intervalo de confiança")
        self.assertContains(resposta, "Cenário fictício")
        evento = RegistroAuditoria.objects.filter(acao="EXPORTAR_EXECUTIVO").latest("id")
        self.assertEqual(evento.detalhes["destino"], "diretoria")
        self.assertEqual(evento.detalhes["sha256"], hashlib.sha256(resposta.content).hexdigest())
        self.assertNotIn("Cenário fictício", str(evento.detalhes))

    def test_documento_escapa_conteudo_e_rejeita_resultado_invalido(self):
        from inventario.aplicacao.visao_executiva import financeiro
        execucao = self.criar_cenario()
        execucao.premissas_snapshot["nome"] = '<img src=x onerror=alert(1)>'
        execucao.save(update_fields=["premissas_snapshot"])
        resposta = self.client.post("/executivo/exportar/", {"destino": "arquivo_local", "execucao": execucao.pk})
        self.assertNotContains(resposta, '<img src=x onerror=alert(1)>')
        self.assertContains(resposta, '&lt;img src=x onerror=alert(1)&gt;', html=False)
        execucao.resultado["perda"]["P95"] = -1
        self.assertIsNone(financeiro(execucao))

    def test_permissoes_csrf_destino_e_rollback(self):
        leitor = get_user_model().objects.create_user("leitor-executivo")
        nomes = [p.split(".")[1] for p in LEITURA]
        leitor.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario", codename__in=nomes))
        self.autenticar(leitor)
        self.assertEqual(self.client.get("/executivo/").status_code, 200)
        self.assertEqual(self.client.post("/executivo/exportar/", {"destino": "diretoria"}).status_code, 403)
        with self.assertRaises(PermissionDenied):
            exportar(leitor, "diretoria")
        self.autenticar(self.usuario)
        csrf = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, csrf)
        self.assertEqual(csrf.post("/executivo/exportar/", {"destino": "diretoria"}).status_code, 403)
        self.assertEqual(self.client.post("/executivo/exportar/", {"destino": "arbitrario"}).status_code, 400)
        with patch("inventario.aplicacao.visao_executiva.registrar_evento", side_effect=RuntimeError("falha")):
            with self.assertRaises(RuntimeError):
                exportar(self.usuario, "diretoria")
        self.assertFalse(RegistroAuditoria.objects.filter(acao="EXPORTAR_EXECUTIVO").exists())

    def test_invalidacao_de_permissao_na_trava(self):
        leitor = get_user_model().objects.create_user("revogado")
        permissoes = [p.split(".")[1] for p in LEITURA] + ["change_incidencia"]
        leitor.user_permissions.set(Permission.objects.filter(content_type__app_label="inventario", codename__in=permissoes))
        def revogar():
            leitor.user_permissions.clear()
        with patch("inventario.aplicacao.visao_executiva.travar_escrita", side_effect=revogar):
            with self.assertRaises(PermissionDenied):
                exportar(leitor, "diretoria")
