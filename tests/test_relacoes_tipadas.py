from datetime import timedelta
import json
from pathlib import Path
import sqlite3
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import Client, SimpleTestCase, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet
from inventario.aplicacao.relacoes import analisar_relacoes, salvar_relacao, LEITURA
from inventario.dominio.grafo_relacoes import GrafoRelacoes
from inventario.infraestrutura.auditoria import verificar_cadeia
from inventario.models import Ativo, RelacaoAtivos, Dependencia, RegistroAuditoria
from .base import BancoTeste


def aresta(pk, origem, destino):
    return {"id": pk, "origem_id": origem, "destino_id": destino}


class MatematicaRelacoes(SimpleTestCase):
    def test_direcao_distancia_caminho_e_origem_nao_contada(self):
        g = GrafoRelacoes(["A", "B", "C", "D"], [aresta(1, "A", "B"), aresta(2, "B", "C")])
        r = g.analisar("A", "C")
        self.assertEqual((r["alcance_base"], r["alvo_base"]["saltos"]), (2, 2))
        self.assertEqual([p["relacao"] for p in r["alvo_base"]["passos"]], [1, 2])
        self.assertEqual(g.analisar("C", "A")["alvo_base"]["alcancavel"], False)
        self.assertEqual(g.analisar("A", "A")["alvo_base"]["saltos"], 0)

    def test_paralelas_e_rota_alternativa_nao_produzem_corte_falso(self):
        g = GrafoRelacoes(["A", "B", "C", "D"], [aresta(1, "A", "B"), aresta(2, "A", "B"),
            aresta(3, "B", "D"), aresta(4, "A", "C"), aresta(5, "C", "D")])
        r = g.analisar("A", "D", remover_relacao=1)
        self.assertEqual(r["perdidos_total"], 0)
        self.assertEqual(r["grau_saida"], 2)
        self.assertNotIn(1, [p["relacao"] for p in r["alvo_cenario"]["passos"]])
        self.assertEqual(g.analisar("A", "D", remover_ativo="B")["alvo_cenario"]["saltos"], 2)

    def test_corte_de_ativo_e_elo_ponte_conta_os_destinos_corretos(self):
        g = GrafoRelacoes(["A", "B", "C", "D"], [aresta(1, "A", "B"), aresta(2, "B", "C")])
        r = g.analisar("A", "C", remover_ativo="B")
        self.assertEqual(r["perdidos"], ["B", "C"])
        self.assertFalse(r["alvo_cenario"]["alcancavel"])
        self.assertEqual(g.analisar("A", remover_relacao=2)["perdidos"], ["C"])
        self.assertEqual(g.analisar("A", remover_ativo="D")["perdidos_total"], 0)

    def test_ciclos_sao_componentes_fortemente_conexas(self):
        g = GrafoRelacoes(list("ABCDE"), [aresta(1, "A", "B"), aresta(2, "B", "A"),
            aresta(3, "B", "C"), aresta(4, "C", "D"), aresta(5, "D", "C")])
        r = g.analisar("A")
        self.assertEqual(r["ciclos_base"]["total_grupos"], 2)
        self.assertEqual({tuple(x["ativos"]) for x in r["ciclos_base"]["grupos"]}, {("A", "B"), ("C", "D")})
        self.assertEqual(r["alcance_base"], 3)

    def test_cadeia_longa_nao_usa_recursao_nem_corta_a_contagem(self):
        nos = [f"N{i}" for i in range(5000)]
        g = GrafoRelacoes(nos, [aresta(i, nos[i-1], nos[i]) for i in range(1, 5000)])
        r = g.analisar(nos[0], nos[-1], limite=1)
        self.assertEqual(r["alcance_base"], 4999)
        self.assertEqual(r["alvo_base"]["saltos"], 4999)
        self.assertFalse(r["alvo_base"]["completo"])
        self.assertEqual(len(r["alvo_base"]["passos"]), 100)
        self.assertEqual(r["alvo_base"]["passos"][0]["origem"], nos[0])
        self.assertTrue(r["limitado"])

    def test_entradas_invalidas_e_limites_sao_rejeitados(self):
        g = GrafoRelacoes(["A", "B"], [aresta(1, "A", "B")])
        for kwargs in ({"origem": "Z"}, {"origem": "A", "destino": "Z"},
                       {"origem": "A", "remover_ativo": "A"}, {"origem": "A", "remover_relacao": 99},
                       {"origem": "A", "limite": True}, {"origem": "A", "limite": 0}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                g.analisar(**kwargs)
        with self.assertRaises(ValueError):
            GrafoRelacoes(["A"], [aresta(1, "A", "B")])
        with self.assertRaises(ValueError):
            GrafoRelacoes(list(range(10001)), [])


class IntegracaoRelacoes(BancoTeste):
    def setUp(self):
        super().setUp()
        self.c = Ativo.objects.create(tipo="1", nome="Banco", fabricante="Dell", sala=self.sala)
        self.hoje = timezone.localdate()

    def dados(self, **kwargs):
        return {"origem_id": self.a.pk, "destino_id": self.b.pk, "tipo": "REDE", "escopo": "homologacao",
                "protocolo": "tcp", "porta": 443, "principal": "", "privilegio": "", "fonte": "regra FW-01",
                "evidencia": "Regra permitida conferida pelo responsável; teste sintético.",
                "observada_em": self.hoje, "revisar_em": self.hoje+timedelta(days=30), "vigente": True, **kwargs}

    def criar(self, **kwargs):
        return salvar_relacao(self.dados(**kwargs), self.usuario)

    def analisar(self, **kwargs):
        return analisar_relacoes(self.usuario, **{"tipo": "REDE", "escopo": "homologacao", "origem": self.a.pk, **kwargs})

    def consulta(self, **kwargs):
        return {"tipo": "REDE", "escopo": "homologacao", "origem": self.a.pk, "limite": 50, **kwargs}

    def operador(self, *permissoes):
        u = get_user_model().objects.create_user("leitor", password="senha-teste-123")
        for p in permissoes:
            app, codename = p.split(".")
            u.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        return u

    def test_cadastro_auditado_tem_autoria_e_nao_altera_modelo_de_risco(self):
        r = self.criar()
        self.assertEqual(r.criada_por, self.usuario)
        self.assertEqual(r.atualizada_por, self.usuario)
        self.assertEqual(Dependencia.objects.count(), 1)
        self.dep.refresh_from_db()
        self.assertEqual(self.dep.peso, .2)
        evento = RegistroAuditoria.objects.filter(entidade="RelacaoAtivos", entidade_id=str(r.pk)).get()
        self.assertEqual(evento.usuario_id, self.usuario.pk)
        self.assertEqual(evento.detalhes["fonte"], "regra FW-01")
        self.assertTrue(verificar_cadeia(False)["integra"])

    def test_validacao_sem_autolaco_porta_identidade_ou_evidencia_incoerentes(self):
        invalidos = [{"destino_id": self.a.pk}, {"porta": 0}, {"porta": 65536}, {"protocolo": "ssh"},
                     {"principal": "DOMINIO\\admin"}, {"evidencia": "   "}, {"evidencia": "a"*4001},
                     {"escopo": "   "}, {"observada_em": self.hoje+timedelta(days=1)},
                     {"revisar_em": self.hoje}, {"observada_em": "data-invalida"},
                     {"tipo": "NEGOCIO"}, {"tipo": "IDENTIDADE", "porta": 0, "protocolo": ""}]
        for d in invalidos:
            with self.subTest(d=d), self.assertRaises(ValidationError):
                self.criar(**d)
        self.assertEqual(RelacaoAtivos.objects.count(), 0)

    def test_mesmo_endpoint_aceita_portas_distintas_sem_duplicar_mesma_relacao(self):
        r = self.criar()
        with self.assertRaises(ValidationError):
            self.criar(escopo=" homologacao ")
        outro = self.criar(porta=8443)
        analise = self.analisar(remover_relacao=r.pk)
        self.assertEqual((analise["total_relacoes"], analise["grau_saida"], analise["alcance_cenario"]), (2, 1, 1))
        self.assertEqual(analise["itens"][0]["passos"][0]["relacao"], outro.pk)

    def test_icmp_sem_porta_e_negocio_sem_protocolos(self):
        self.criar(protocolo="icmp", porta=0)
        self.criar(tipo="NEGOCIO", protocolo="", porta=0)
        self.assertEqual(self.analisar()["total_relacoes"], 1)
        self.assertEqual(self.analisar(tipo="NEGOCIO")["total_relacoes"], 1)

    def test_camadas_escopos_e_principais_nao_sao_concatenados(self):
        self.criar()
        self.criar(origem_id=self.b.pk, destino_id=self.c.pk, tipo="NEGOCIO", protocolo="", porta=0)
        self.criar(origem_id=self.b.pk, destino_id=self.c.pk, escopo="producao")
        self.assertEqual(self.analisar()["alcance_base"], 1)
        for origem, destino, principal in [(self.a, self.b, "corp/svc-a"), (self.b, self.c, "corp/svc-b")]:
            self.criar(origem_id=origem.pk, destino_id=destino.pk, tipo="IDENTIDADE", protocolo="", porta=0,
                       principal=principal, privilegio="ADMIN")
        self.assertEqual(self.analisar(tipo="IDENTIDADE", principal="corp/svc-a")["alcance_base"], 1)
        for kwargs in ({"tipo": "IDENTIDADE"}, {"principal": "corp/svc-a"}, {"tipo": "TODAS"}, {"escopo": ""}):
            with self.assertRaises(ValueError):
                self.analisar(**kwargs)

    def test_exclui_vencidas_revogadas_inativas_sem_cache(self):
        r = self.criar()
        self.assertEqual(self.analisar()["alcance_base"], 1)
        with patch("inventario.aplicacao.relacoes.timezone.localdate", return_value=r.revisar_em):
            resultado = self.analisar()
            self.assertEqual((resultado["alcance_base"], resultado["excluidas"]), (0, 1))
        salvar_relacao({"vigente": False}, self.usuario, r.pk, r.atualizado_em.isoformat())
        self.assertEqual(self.analisar()["alcance_base"], 0)
        r.refresh_from_db()
        salvar_relacao({"vigente": True}, self.usuario, r.pk, r.atualizado_em.isoformat())
        self.b.status = "INATIVO"
        self.b.save()
        self.assertEqual(self.analisar()["excluidas"], 1)

    def test_simulacao_e_get_nao_modificam_cadastros(self):
        r = self.criar()
        antes = list(RelacaoAtivos.objects.values())
        resposta = self.client.get("/api/grafo-relacoes/", self.consulta(remover_relacao=r.pk, destino=self.b.pk))
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()["perdidos_total"], 1)
        self.assertEqual(list(RelacaoAtivos.objects.values()), antes)
        self.assertEqual(self.client.get("/relacoes/").status_code, 200)
        self.assertEqual(self.client.get(f"/relacoes/{r.pk}/editar/").status_code, 200)
        self.assertEqual(RelacaoAtivos.objects.count(), 1)

    def test_edicao_usa_versao_evitar_sobrescrever_alteracao_concorrente(self):
        r = self.criar()
        versao = r.atualizado_em.isoformat()
        # Simula o relógio de baixa resolução observado no Windows.
        with patch("django.db.models.fields.timezone.now", return_value=r.atualizado_em):
            salvar_relacao({"evidencia": "Revisão feita por outro operador"}, self.usuario, r.pk, versao)
            with self.assertRaises(ValidationError):
                salvar_relacao({"vigente": False}, self.usuario, r.pk, versao)
        r.refresh_from_db()
        self.assertTrue(r.vigente)
        self.assertEqual(r.evidencia, "Revisão feita por outro operador")

    def test_versao_avanca_em_gravacoes_seguidas_com_relogio_retrocedendo(self):
        r = self.criar()
        inicial = r.atualizado_em
        with patch("django.db.models.fields.timezone.now", return_value=inicial-timedelta(microseconds=1)):
            primeiro = salvar_relacao({"evidencia": "Primeira revisão"}, self.usuario, r.pk, inicial.isoformat())
            segundo = salvar_relacao({"evidencia": "Segunda revisão"}, self.usuario, r.pk, primeiro.atualizado_em.isoformat())
        self.assertGreater(primeiro.atualizado_em, inicial)
        self.assertGreater(segundo.atualizado_em, primeiro.atualizado_em)
        r.refresh_from_db()
        self.assertEqual(r.atualizado_em, segundo.atualizado_em)
        self.assertEqual(r.evidencia, "Segunda revisão")

    def test_formulario_rejeita_versao_antiga_e_preserva_a_alteracao(self):
        r = self.criar()
        antiga = r.atualizado_em.isoformat()
        with patch("django.db.models.fields.timezone.now", return_value=r.atualizado_em):
            salvar_relacao({"evidencia": "Atualização confirmada"}, self.usuario, r.pk, antiga)
            dados = self.dados(evidencia="Formulário antigo")
            dados["origem"] = dados.pop("origem_id")
            dados["destino"] = dados.pop("destino_id")
            dados["versao"] = antiga
            resposta = self.client.post(f"/relacoes/{r.pk}/editar/", dados)
        self.assertContains(resposta, "A relação mudou; recarregue antes de editar.")
        r.refresh_from_db()
        self.assertEqual(r.evidencia, "Atualização confirmada")

    def test_save_com_update_fields_tambem_invalida_versao_antiga(self):
        r = self.criar()
        antiga = r.atualizado_em.isoformat()
        with patch("django.db.models.fields.timezone.now", return_value=r.atualizado_em):
            r.evidencia = "Alteração pelo cadastro administrativo"
            r.save(update_fields=["evidencia"])
            with self.assertRaises(ValidationError):
                salvar_relacao({"evidencia": "Tentativa antiga"}, self.usuario, r.pk, antiga)
        r.refresh_from_db()
        self.assertEqual(r.evidencia, "Alteração pelo cadastro administrativo")

    def test_campos_de_autoria_nao_podem_ser_injetados_no_servico(self):
        for extra in ({"criada_por_id": self.usuario.pk}, {"atualizado_em": timezone.now()}, {"id": 100}):
            with self.assertRaises(ValidationError):
                salvar_relacao(self.dados(**extra), self.usuario)

    def test_leitor_consulta_mas_nao_cadastra_edita_ou_acessa_admin(self):
        r = self.criar()
        u = self.operador(*LEITURA)
        self.autenticar(u)
        for url in ("/relacoes/", "/grafo-relacoes/", "/api/grafo-relacoes/"):
            self.assertEqual(self.client.get(url, self.consulta()).status_code, 200)
        self.assertEqual(self.client.get("/relacoes/nova/").status_code, 403)
        self.assertEqual(self.client.post(f"/relacoes/{r.pk}/editar/", {}).status_code, 403)
        self.assertEqual(self.client.get("/admin/auth/user/").status_code, 403)
        with self.assertRaises(PermissionDenied):
            salvar_relacao(self.dados(porta=80), u)

    def test_sem_permissao_relacoes_nao_le_api_nem_evidencias(self):
        u = self.operador("inventario.view_ativo")
        self.autenticar(u)
        for url in ("/relacoes/", "/grafo-relacoes/", "/api/grafo-relacoes/"):
            self.assertEqual(self.client.get(url, self.consulta()).status_code, 403)
        with self.assertRaises(PermissionDenied):
            analisar_relacoes(u, "REDE", "homologacao", self.a.pk)

    def test_conta_inativa_e_permissao_em_cache_revogada_bloqueiam_servico(self):
        u = self.operador(*LEITURA, "inventario.add_relacaoativos")
        self.assertTrue(u.has_perm("inventario.add_relacaoativos"))
        u.user_permissions.remove(Permission.objects.get(codename="add_relacaoativos"))
        with self.assertRaises(PermissionDenied):
            salvar_relacao(self.dados(), u)
        get_user_model().objects.filter(pk=self.usuario.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.analisar()

    def test_mfa_obrigatorio_e_escrita_exige_totp(self):
        from inventario.seguranca_mfa import usuario_privilegiado
        u = self.operador(*LEITURA, "inventario.add_relacaoativos")
        self.assertTrue(usuario_privilegiado(u))
        c = Client()
        c.force_login(u)
        self.assertEqual(c.get("/relacoes/").status_code, 302)
        self.assertIn("/mfa/", c.get("/relacoes/").url)

    def test_post_sem_csrf_bloqueado_e_api_nao_aceita_post(self):
        c = Client(enforce_csrf_checks=True)
        self.autenticar(self.usuario, c)
        self.assertEqual(c.post("/relacoes/nova/", {}).status_code, 403)
        self.assertEqual(self.client.post("/api/grafo-relacoes/", self.consulta()).status_code, 405)
        self.assertEqual(RelacaoAtivos.objects.count(), 0)

    def test_upload_web_formulario_grava_mesmo_servico_e_escapa_html(self):
        dados = self.dados(fonte='<script>alert("x")</script>')
        dados["origem"], dados["destino"] = dados.pop("origem_id"), dados.pop("destino_id")
        resposta = self.client.post("/relacoes/nova/", dados)
        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(RelacaoAtivos.objects.count(), 1)
        for url in ("/relacoes/", "/grafo-relacoes/"):
            r = self.client.get(url, self.consulta())
            self.assertEqual(r.status_code, 200)
            self.assertContains(r, "&lt;script&gt;")
            self.assertNotContains(r, '<script>alert("x")</script>')

    def test_api_erros_utilizaveis_sem_chamada_externa(self):
        with patch("socket.socket.connect", side_effect=AssertionError("rede não autorizada")):
            self.criar()
            r = self.client.get("/api/grafo-relacoes/", self.consulta())
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()["total_relacoes"], 1)
        for d in ({"tipo": "TODAS"}, {"origem": "inexistente"}, {"limite": 101},
                  {"remover_relacao": 0}, {"remover_ativo": self.a.pk}, {"principal": "outro"}):
            r = self.client.get("/api/grafo-relacoes/", self.consulta(**d))
            self.assertEqual(r.status_code, 400, r.content)
            self.assertIn("erro", r.json())

    def test_snapshot_muda_com_evidencia_e_cenario_nao_altera_entrada(self):
        r = self.criar()
        h = self.analisar()["snapshot_sha256"]
        self.assertEqual(h, self.analisar(remover_relacao=r.pk)["snapshot_sha256"])
        salvar_relacao({"evidencia": "Nova verificação"}, self.usuario, r.pk, r.atualizado_em.isoformat())
        self.assertNotEqual(h, self.analisar()["snapshot_sha256"])

    def test_evidencia_nova_pede_reavaliacao_ssvc_sem_reescrever_decisao(self):
        from inventario.aplicacao.ssvc import contexto_atual, registrar_avaliacao, situacao
        _, assinatura = contexto_atual(self.i)
        status = self.i.status
        registro = registrar_avaliacao(self.i.pk, self.usuario,
            {"exploitation": "active", "exposure": "open", "automatable": "yes", "human_impact": "high"},
            "Evidência sintética do contexto inicial", self.hoje+timedelta(days=30), assinatura, "Patch aprovado")
        resultado = registro.resultado.copy()
        self.criar()
        registro.refresh_from_db()
        self.assertEqual(registro.resultado, resultado)
        self.assertEqual(situacao(registro, contexto_atual(self.i)[1]), "Reavaliar: contexto alterado")
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, status)

    def test_ssvc_percebe_mudanca_sem_expor_principal_ou_evidencia(self):
        from inventario.aplicacao.ssvc import contexto_atual
        contexto, antes = contexto_atual(self.i)
        r = self.criar(tipo="IDENTIDADE", protocolo="", porta=0, principal="conta-restrita", privilegio="ADMIN")
        novo, depois = contexto_atual(self.i)
        self.assertNotEqual(antes, depois)
        self.assertNotIn("conta-restrita", json.dumps(novo))
        self.assertNotIn(r.evidencia, json.dumps(novo))
        self.assertNotIn("relacoes_do_ativo_sha256", contexto)
        with patch("inventario.aplicacao.ssvc.timezone.localdate", return_value=r.revisar_em):
            self.assertNotEqual(depois, contexto_atual(self.i)[1])

    def test_banco_impede_autolaco_e_porta_incoerente_mesmo_sem_model_clean(self):
        r = self.criar()
        for d in ({"destino_id": self.a.pk}, {"porta": 0}, {"tipo": "INVALIDO"}, {"revisar_em": self.hoje}):
            with self.subTest(d=d), self.assertRaises(IntegrityError), transaction.atomic():
                RelacaoAtivos.objects.filter(pk=r.pk).update(**d)

    def test_ativo_com_evidencia_nao_pode_ser_excluido_em_cascata(self):
        self.criar()
        with self.assertRaises(ProtectedError):
            self.a.delete()

    def test_exportacao_e_backup_restauram_relacoes_com_autoria_e_evidencia(self):
        from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
        from inventario.infraestrutura.exportacao import inventario_completo
        r = self.criar()
        colecao = inventario_completo()["colecoes"]["relacaoativos"]
        self.assertEqual(colecao[0]["fonte"], r.fonte)
        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode(), SAURON_BACKUP_DESTINO_ADICIONAL=""):
            arquivo = backup_sqlite()
            destino = Path(self.diretorio.name)/"fase4-restaurado.sqlite3"
            restaurar_backup(arquivo, destino)
        with sqlite3.connect(destino) as db:
            self.assertEqual(db.execute("SELECT origem_id, destino_id, fonte, criada_por_id FROM inventario_relacaoativos").fetchone(),
                             (self.a.pk, self.b.pk, r.fonte, self.usuario.pk))

    def test_terminal_analisa_mesmo_resultado_da_api(self):
        from inventario.cli_menus.relacoes import analisar
        self.criar()
        cli = Mock(usuario=self.usuario)
        cli._exigir.return_value = True
        cli._texto.side_effect = ["REDE", "homologacao", self.b.pk, "", ""]
        cli._ativo.return_value = self.a
        analisar(cli)
        esperado = self.analisar(destino=self.b.pk)
        self.assertEqual(json.loads(cli.saida.call_args.args[0]), json.loads(json.dumps(esperado, default=str)))

    def test_terminal_perda_de_permissao_na_confirmacao_impede_gravacao(self):
        from inventario.cli_menus.relacoes import relacoes
        cli = Mock(usuario=self.usuario)
        cli._exigir.return_value = True
        cli._texto.side_effect = ["3", "REDE", "homologacao", "tcp", "Fonte", "Evidência", str(self.hoje), str(self.hoje+timedelta(days=30))]
        cli._ativo.side_effect = [self.a, self.b]
        cli._inteiro.return_value = 443
        def confirmar(_):
            get_user_model().objects.filter(pk=self.usuario.pk).update(is_active=False)
            return True
        cli._confirmar.side_effect = confirmar
        with self.assertRaises(PermissionDenied):
            relacoes(cli)
        self.assertFalse(RelacaoAtivos.objects.exists())

    def test_grupos_oficiais_separam_consulta_e_manutencao(self):
        from django.contrib.auth.models import Group
        from inventario.management.commands.configurar_grupos import configurar_grupos
        configurar_grupos()
        for nome in ("Operadores", "Auditores", "Gerentes"):
            codigos = set(Group.objects.get(name=nome).permissions.values_list("codename", flat=True))
            self.assertIn("view_relacaoativos", codigos)
            self.assertEqual("add_relacaoativos" in codigos, nome == "Gerentes")
            self.assertEqual("change_relacaoativos" in codigos, nome == "Gerentes")
            self.assertNotIn("delete_relacaoativos", codigos)

    def test_evidencia_individual_e_link_do_caminho_estao_conectados(self):
        r = self.criar()
        html = self.client.get("/grafo-relacoes/", self.consulta(destino=self.b.pk))
        self.assertContains(html, f'/relacoes/{r.pk}/')
        self.assertContains(self.client.get(f"/relacoes/{r.pk}/"), r.evidencia)
        self.assertEqual(self.client.get("/relacoes/999999/").status_code, 404)

    def test_recorte_excessivo_e_rejeitado_sem_calcular_parte_do_inventario(self):
        with patch("inventario.aplicacao.relacoes.MAX_NOS", 2), self.assertRaises(ValueError):
            self.analisar()
        self.criar()
        with patch("inventario.aplicacao.relacoes.MAX_ARESTAS", 0), self.assertRaises(ValueError):
            self.analisar()
