from datetime import date, timedelta
import json
from pathlib import Path
import re
import sqlite3
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models.deletion import ProtectedError
from django.test import Client, SimpleTestCase, override_settings
from django.utils import timezone
from cryptography.fernet import Fernet
from inventario.aplicacao.cobertura import LEITURA, salvar_perimetro, preparar_revisao, registrar_revisao, analisar_cobertura
from inventario.aplicacao.relacoes import salvar_relacao, analisar_relacoes
from inventario.dominio.cobertura import contextos, motivo, percentual, estado
from inventario.models import Ativo, PerimetroRelacoes, RevisaoCobertura, RegistroAuditoria
from .base import BancoTeste


class MetricasCobertura(SimpleTestCase):
    def setUp(self):
        self.hoje = date(2026, 11, 2)
        self.ativos = [{"id": "A", "status": "ATIVO"}, {"id": "B", "status": "ATIVO"}]
        self.r = {"id": 1, "origem_id": "A", "destino_id": "B", "vigente": True,
                  "observada_em": self.hoje, "revisar_em": self.hoje+timedelta(days=10),
                  "origem__status": "ATIVO", "destino__status": "ATIVO"}

    def test_percentual_sem_denominador_nao_vira_cem(self):
        self.assertIsNone(percentual(0, 0))
        self.assertEqual(percentual(0, 2), 0)
        self.assertEqual(percentual(1, 3), 33.33)

    def test_motivos_exclusivos_com_precedencia_explicita(self):
        ids = {"A", "B"}
        alteracoes = [({}, "ELEGIVEL"), ({"vigente": False, "revisar_em": self.hoje}, "REVOGADA"),
                      ({"observada_em": self.hoje+timedelta(days=1)}, "OBSERVACAO_FUTURA"),
                      ({"revisar_em": self.hoje}, "VENCIDA"), ({"destino__status": "INATIVO"}, "ATIVO_INATIVO"),
                      ({"destino_id": "C"}, "FORA_PERIMETRO")]
        for d, esperado in alteracoes:
            self.assertEqual(motivo({**self.r, **d}, ids, self.hoje), esperado)

    def test_contexto_nao_muda_diariamente_mas_muda_no_vencimento(self):
        def sha(hoje, tipo="REDE", principal=""):
            return contextos(self.ativos, [self.r], 1, hoje, tipo, principal)[0]["A"]["sha256"]
        self.assertEqual(sha(self.hoje), sha(self.hoje+timedelta(days=1)))
        self.assertNotEqual(sha(self.hoje), sha(self.r["revisar_em"]))
        self.assertNotEqual(sha(self.hoje), sha(self.hoje, "IDENTIDADE", "conta"))

    def test_membro_novo_sem_vinculo_nao_invalida_revisao_de_outro_ativo(self):
        antes = contextos(self.ativos, [self.r], 1, self.hoje, "REDE", "")[0]
        depois = contextos(self.ativos+[{"id": "C", "status": "ATIVO"}], [self.r], 1, self.hoje, "REDE", "")[0]
        self.assertEqual(antes["A"]["sha256"], depois["A"]["sha256"])
        self.assertEqual(depois["C"]["vigentes"], 0)

    def test_estado_ausencia_de_revisao_e_prazo_sao_distintos(self):
        c = {"sha256": "atual"}
        r = {"contexto_sha256": "atual", "revisar_em": self.hoje, "resultado": "SEM_RELACOES"}
        self.assertEqual(estado(None, c, self.hoje), "SEM_REVISAO")
        self.assertEqual(estado(r, c, self.hoje), "REVISAO_VENCIDA")
        self.assertEqual(estado({**r, "contexto_sha256": "anterior"}, c, self.hoje), "CONTEXTO_ALTERADO")


class FluxoCobertura(BancoTeste):
    def setUp(self):
        super().setUp()
        self.hoje = timezone.localdate()
        self.c = Ativo.objects.create(tipo="1", nome="Terceiro", fabricante="Equipe", sala=self.sala)

    def perimetro(self, ids=None):
        return salvar_perimetro(self.usuario, "homologacao", "Perímetro sintético explicitamente declarado", ids if ids is not None else [self.a.pk, self.b.pk])

    def relacao(self, **extras):
        return salvar_relacao({"origem_id": self.a.pk, "destino_id": self.b.pk, "tipo": "REDE", "escopo": "homologacao",
            "protocolo": "tcp", "porta": 443, "principal": "", "privilegio": "", "fonte": "Regra de teste",
            "evidencia": "Verificação sintética", "observada_em": self.hoje, "revisar_em": self.hoje+timedelta(days=10), "vigente": True, **extras}, self.usuario)

    def revisar(self, p, resultado="SEM_RELACOES", ativo=None, **extras):
        ativo = ativo or self.a.pk
        tipo, principal = extras.pop("tipo", "REDE"), extras.pop("principal", "")
        _, c = preparar_revisao(self.usuario, p.pk, tipo, ativo, principal)
        return registrar_revisao(self.usuario, **{"perimetro": p.pk, "tipo": tipo, "ativo": ativo, "principal": principal,
            "resultado": resultado, "evidencia": "Fontes consultadas e limitações documentadas; exemplo sintético",
            "observada_em": self.hoje, "revisar_em": self.hoje+timedelta(days=20), "contexto_sha256": c["sha256"], **extras})

    def consulta(self, p, **extras):
        return analisar_cobertura(self.usuario, p.pk, **{"tipo": "REDE", **extras})

    def usuario_com(self, *permissoes):
        u = get_user_model().objects.create_user("analista", password="senha-teste-123")
        for permissao in permissoes:
            app, codename = permissao.split(".")
            u.user_permissions.add(Permission.objects.get(content_type__app_label=app, codename=codename))
        return u

    def test_perimetro_limita_grafo_sem_inferir_membros_de_dados_legados(self):
        self.relacao()
        self.relacao(origem_id=self.b.pk, destino_id=self.c.pk)
        antes = analisar_relacoes(self.usuario, "REDE", "homologacao", self.a.pk)
        self.assertEqual(antes["alcance_base"], 2)
        self.assertIsNone(antes["perimetro_id"])
        p = self.perimetro()
        depois = analisar_relacoes(self.usuario, "REDE", "homologacao", self.a.pk)
        self.assertEqual((depois["alcance_base"], depois["total_ativos"], depois["excluidas"]), (1, 2, 1))
        self.assertEqual(self.consulta(p)["motivos_relacoes"]["FORA_PERIMETRO"], 1)

    def test_denominador_explicitamente_vazio_ou_sem_membros_operacionais(self):
        p = self.perimetro([])
        r = self.consulta(p)
        self.assertIsNone(r["cobertura_declarada_percentual"])
        self.assertEqual(r["ativos_operacionais"], 0)
        self.a.status = "INATIVO"
        self.a.save()
        p = salvar_perimetro(self.usuario, p.nome, p.descricao, [self.a.pk], p.pk, p.atualizado_em.isoformat())
        r = self.consulta(p)
        self.assertEqual((r["membros_total"], r["ativos_excluidos"]), (1, 1))
        self.assertIsNone(r["representacao_percentual"])

    def test_sem_revisao_nao_e_ausencia_verificada(self):
        p = self.perimetro()
        self.assertEqual(self.consulta(p)["estados"]["SEM_REVISAO"], 2)
        self.revisar(p)
        r = self.consulta(p)
        self.assertEqual((r["revisados_no_prazo"], r["cobertura_declarada_percentual"]), (1, 50))
        self.assertEqual(r["representacao_percentual"], 0)

    def test_ter_vinculo_nao_significa_ter_revisao(self):
        p = self.perimetro()
        self.relacao()
        antes = self.consulta(p)
        self.assertEqual((antes["representacao_percentual"], antes["cobertura_declarada_percentual"]), (100, 0))
        self.revisar(p, "REVISADO")
        self.assertEqual(self.consulta(p)["cobertura_declarada_percentual"], 50)

    def test_ausencia_e_revisao_completa_sao_bloqueadas_com_pendencias_vigentes(self):
        p = self.perimetro()
        self.relacao(observada_em=self.hoje-timedelta(days=10), revisar_em=self.hoje)
        for resultado in ("SEM_RELACOES", "REVISADO"):
            with self.assertRaises(ValidationError):
                self.revisar(p, resultado)
        self.revisar(p, "LACUNAS")
        self.assertEqual(self.consulta(p)["estados"]["LACUNAS"], 1)
        self.assertEqual(self.consulta(p)["revisados_no_prazo"], 0)

    def test_revisado_exige_ao_menos_um_vinculo_elegivel(self):
        p = self.perimetro()
        with self.assertRaises(ValidationError):
            self.revisar(p, "REVISADO")
        self.assertEqual(RevisaoCobertura.objects.count(), 0)

    def test_revogadas_preservadas_nao_impedem_declaracao_de_ausencia(self):
        p = self.perimetro()
        self.relacao(vigente=False)
        self.revisar(p)
        r = self.consulta(p)
        self.assertEqual(r["motivos_relacoes"]["REVOGADA"], 1)
        self.assertEqual(r["estados"]["SEM_RELACOES"], 1)

    def test_revisao_vencida_e_contexto_alterado_nao_entram_no_numerador(self):
        p = self.perimetro()
        r = self.revisar(p)
        with patch("django.utils.timezone.localdate", return_value=r.revisar_em):
            self.assertEqual(self.consulta(p)["estados"]["REVISAO_VENCIDA"], 1)
        self.relacao()
        self.assertEqual(self.consulta(p)["estados"]["CONTEXTO_ALTERADO"], 1)
        self.assertEqual(self.consulta(p)["revisados_no_prazo"], 0)

    def test_alteracao_de_membro_com_vinculo_invalida_contexto_afetado(self):
        p = self.perimetro([self.a.pk])
        self.relacao()
        self.revisar(p, "LACUNAS")
        salvar_perimetro(self.usuario, p.nome, p.descricao, [self.a.pk, self.b.pk], p.pk, p.atualizado_em.isoformat())
        r = self.consulta(p)
        self.assertEqual(r["estados"]["CONTEXTO_ALTERADO"], 1)
        self.assertEqual(r["estados"]["SEM_REVISAO"], 1)

    def test_definicao_do_perimetro_tambem_vincula_revisao_e_contexto_ssvc(self):
        from inventario.aplicacao.ssvc import contexto_atual
        p = self.perimetro()
        revisao = self.revisar(p)
        antes = contexto_atual(self.i)[1]
        salvar_perimetro(self.usuario, p.nome, "Definição revisada do escopo", [self.a.pk, self.b.pk], p.pk, p.atualizado_em.isoformat())
        self.assertEqual(self.consulta(p)["estados"]["CONTEXTO_ALTERADO"], 1)
        self.assertNotEqual(antes, contexto_atual(self.i)[1])
        revisao.refresh_from_db()
        self.assertEqual(revisao.resultado, "SEM_RELACOES")

    def test_revisao_de_ativo_fora_ou_inativo_e_bloqueada(self):
        p = self.perimetro()
        with self.assertRaises(ValidationError):
            self.revisar(p, ativo=self.c.pk)
        self.a.status = "BAIXADO"
        self.a.save()
        with self.assertRaises(ValidationError):
            self.revisar(p)

    def test_contexto_antigo_e_forma_ambigua_nao_gravam(self):
        p = self.perimetro()
        _, c = preparar_revisao(self.usuario, p.pk, "REDE", self.a.pk)
        self.relacao()
        with self.assertRaises(ValidationError):
            self.revisar(p, "LACUNAS", contexto_sha256=c["sha256"])
        resposta = self.client.post("/cobertura/revisar/", {"perimetro": p.pk, "tipo": "REDE", "ativo": self.a.pk,
            "principal": "", "resultado": "LACUNAS", "evidencia": "Prévia desatualizada",
            "observada_em": self.hoje.isoformat(), "revisar_em": (self.hoje+timedelta(days=20)).isoformat(), "contexto_sha256": c["sha256"]})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "recarregue o contexto")
        self.assertFalse(RevisaoCobertura.objects.exists())

    def test_revisao_historica_ultima_nao_regride_para_uma_mais_antiga(self):
        p = self.perimetro()
        antiga = self.revisar(p)
        nova = self.revisar(p, "LACUNAS")
        self.assertEqual(self.consulta(p)["itens"][0]["revisao_id"], nova.pk)
        self.assertEqual(self.consulta(p)["estados"]["SEM_RELACOES"], 0)
        antiga.evidencia = "Tentativa de reescrever"
        with self.assertRaises(ValidationError):
            antiga.save()

    def test_principal_e_camada_isolados_mesmo_sem_relacoes(self):
        p = self.perimetro()
        self.revisar(p, tipo="IDENTIDADE", principal="dominio/svc-a")
        self.assertEqual(self.consulta(p, tipo="IDENTIDADE", principal="dominio/svc-a")["revisados_no_prazo"], 1)
        self.assertEqual(self.consulta(p, tipo="IDENTIDADE", principal="dominio/svc-b")["revisados_no_prazo"], 0)
        self.assertEqual(self.consulta(p)["revisados_no_prazo"], 0)

    def test_perimetro_edicao_concorrente_nome_e_ids_invalidos_sao_atomicos(self):
        p = self.perimetro()
        versao = p.atualizado_em.isoformat()
        for nome, ids in (("outro", [self.a.pk]), (p.nome, ["INEXISTENTE"]), (p.nome, [self.a.pk]*2)):
            with self.assertRaises(ValidationError):
                salvar_perimetro(self.usuario, nome, "Descrição", ids, p.pk, versao)
        salvar_perimetro(self.usuario, p.nome, "Nova descrição", [self.a.pk], p.pk, versao)
        with self.assertRaises(ValidationError):
            salvar_perimetro(self.usuario, p.nome, "Concorrente", [self.b.pk], p.pk, versao)
        self.assertEqual(list(p.ativos.values_list("pk", flat=True)), [self.a.pk])

    def test_datas_e_evidencia_invalidas_nao_passam(self):
        p = self.perimetro()
        for extras in ({"evidencia": "   "}, {"evidencia": "x"*4001}, {"observada_em": self.hoje+timedelta(days=1)},
                       {"revisar_em": self.hoje}, {"revisar_em": self.hoje+timedelta(days=91)}, {"resultado": "SEGURO"}):
            with self.subTest(extras=extras), self.assertRaises(ValidationError):
                self.revisar(p, **extras)

    def test_filtro_de_exibicao_nao_altera_denominador(self):
        p = self.perimetro()
        self.revisar(p)
        r = self.consulta(p, filtro="SEM_REVISAO", limite=1)
        self.assertEqual(r["ativos_operacionais"], 2)
        self.assertEqual(r["cobertura_declarada_percentual"], 50)
        self.assertEqual(len(r["itens"]), 1)
        self.assertEqual(r["itens"][0]["ativo"], self.b.pk)

    def test_membros_e_autoria_ficam_auditados_sem_alterar_risco(self):
        status = self.i.status
        p = self.perimetro()
        r = self.revisar(p)
        self.assertEqual(RegistroAuditoria.objects.get(acao="PERIMETRO_MEMBROS").detalhes["total"], 2)
        evento = RegistroAuditoria.objects.get(acao="COBERTURA_REVISADA", entidade_id=str(r.pk))
        self.assertEqual(evento.usuario_id, self.usuario.pk)
        self.i.refresh_from_db()
        self.assertEqual(self.i.status, status)
        with self.assertRaises(ProtectedError):
            self.a.delete()

    def test_ssvc_recebe_hash_sem_expor_evidencia_ou_principal(self):
        from inventario.aplicacao.ssvc import contexto_atual
        antes, h1 = contexto_atual(self.i)
        self.assertNotIn("cobertura_declarada_sha256", antes)
        p = self.perimetro()
        r = self.revisar(p, tipo="IDENTIDADE", principal="conta-sensivel")
        contexto, h2 = contexto_atual(self.i)
        self.assertNotEqual(h1, h2)
        self.assertNotIn("conta-sensivel", json.dumps(contexto))
        self.assertNotIn(r.evidencia, json.dumps(contexto))
        with patch("django.utils.timezone.localdate", return_value=r.revisar_em):
            self.assertNotEqual(h2, contexto_atual(self.i)[1])

    def test_leitor_nao_grava_e_usuario_sem_permissoes_nao_consulta(self):
        p = self.perimetro()
        u = self.usuario_com(*LEITURA)
        self.autenticar(u)
        self.assertEqual(self.client.get("/qualidade-relacoes/").status_code, 200)
        self.assertEqual(self.client.post("/perimetros/novo/", {}).status_code, 403)
        self.assertEqual(self.client.get("/cobertura/revisar/").status_code, 403)
        self.assertEqual(self.client.get("/admin/auth/user/").status_code, 403)
        with self.assertRaises(PermissionDenied):
            salvar_perimetro(u, "novo", "Descrição", [self.a.pk])
        u.user_permissions.clear()
        with self.assertRaises(PermissionDenied):
            analisar_cobertura(u, p.pk, "REDE")

    def test_revogacao_de_permissao_em_cache_e_conta_inativa_bloqueiam(self):
        u = self.usuario_com(*LEITURA, "inventario.add_perimetrorelacoes")
        self.assertTrue(u.has_perm("inventario.add_perimetrorelacoes"))
        u.user_permissions.remove(Permission.objects.get(codename="add_perimetrorelacoes"))
        with self.assertRaises(PermissionDenied):
            salvar_perimetro(u, "novo", "Descrição", [])
        get_user_model().objects.filter(pk=self.usuario.pk).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            self.perimetro()

    def test_mfa_csrf_e_metodos_http(self):
        p = self.perimetro()
        c = Client(enforce_csrf_checks=True)
        c.force_login(self.usuario)
        self.assertEqual(c.get("/qualidade-relacoes/").status_code, 200)
        self.autenticar(self.usuario, c)
        self.assertEqual(c.post("/perimetros/novo/", {}).status_code, 403)
        self.assertEqual(c.post("/cobertura/revisar/", {}).status_code, 403)
        self.assertEqual(self.client.post("/api/qualidade-relacoes/", {"perimetro": p.pk, "tipo": "REDE"}).status_code, 405)

    def test_revisor_comum_exige_totp_e_registra_sem_receber_administracao(self):
        from inventario.seguranca_mfa import usuario_privilegiado
        p = self.perimetro()
        u = self.usuario_com(*LEITURA, "inventario.add_revisaocobertura")
        self.assertTrue(usuario_privilegiado(u))
        self.autenticar(u)
        _, resumo = preparar_revisao(u, p.pk, "REDE", self.a.pk)
        r = registrar_revisao(u, p.pk, "REDE", self.a.pk, "", "SEM_RELACOES", "Revisão sintética", self.hoje,
                             self.hoje+timedelta(days=90), resumo["sha256"])
        self.assertEqual(r.por, u)
        self.assertEqual(self.client.get("/admin/auth/user/").status_code, 403)
        self.assertEqual(self.client.get(f"/perimetros/{p.pk}/editar/").status_code, 403)

    def test_formularios_revisao_detalhe_api_e_links_funcionam(self):
        resposta = self.client.post("/perimetros/novo/", {"nome": "homologacao", "descricao": "Homologação", "ativos": [self.a.pk, self.b.pk]})
        self.assertEqual(resposta.status_code, 302)
        p = PerimetroRelacoes.objects.get()
        params = {"perimetro": p.pk, "tipo": "REDE", "ativo": self.a.pk}
        previa = self.client.get("/cobertura/revisar/", params)
        self.assertEqual(previa.status_code, 200)
        sha = re.search(r'name="contexto_sha256" value="([a-f0-9]{64})"', previa.content.decode()).group(1)
        d = {**params, "principal": "", "resultado": "SEM_RELACOES", "evidencia": "<script>alert(1)</script>",
             "observada_em": self.hoje.isoformat(), "revisar_em": (self.hoje+timedelta(days=10)).isoformat(), "contexto_sha256": sha}
        r = self.client.post("/cobertura/revisar/", d)
        self.assertEqual(r.status_code, 302, r.content)
        self.assertContains(self.client.get(r.url), "&lt;script&gt;")
        painel = self.client.get("/qualidade-relacoes/", params)
        self.assertEqual(painel.status_code, 200)
        self.assertContains(painel, r.url)
        api = self.client.get("/api/qualidade-relacoes/", params)
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api.json()["cobertura_declarada_percentual"], 50)

    def test_get_invalido_de_revisao_retorna_erro_util_sem_excecao(self):
        p = self.perimetro()
        for params in ({"perimetro": p.pk, "tipo": "REDE", "ativo": self.c.pk},
                       {"perimetro": 99999, "tipo": "REDE", "ativo": self.a.pk}):
            self.assertEqual(self.client.get("/cobertura/revisar/", params).status_code, 200)
        self.assertEqual(self.client.get("/cobertura/99999/").status_code, 404)

    def test_api_invalida_e_consulta_sem_rede_ou_gravacoes(self):
        p = self.perimetro()
        antes = RegistroAuditoria.objects.count()
        with patch("socket.socket.connect", side_effect=AssertionError("não consultar rede")):
            self.assertEqual(self.client.get("/api/qualidade-relacoes/", {"perimetro": p.pk, "tipo": "REDE"}).status_code, 200)
        self.assertEqual(RegistroAuditoria.objects.count(), antes)
        for extra in ({"tipo": "TODAS"}, {"principal": "conta"}, {"limite": 101}, {"filtro": "SEGURO"}):
            r = self.client.get("/api/qualidade-relacoes/", {"perimetro": p.pk, "tipo": "REDE", **extra})
            self.assertEqual(r.status_code, 400)

    def test_grupos_oficiais_operador_revisa_auditor_so_consulta(self):
        from inventario.management.commands.configurar_grupos import configurar_grupos
        configurar_grupos()
        for nome in ("Gerentes", "Operadores", "Auditores"):
            permissoes = set(Group.objects.get(name=nome).permissions.values_list("codename", flat=True))
            self.assertIn("view_revisaocobertura", permissoes)
            self.assertEqual("add_revisaocobertura" in permissoes, nome != "Auditores")
            self.assertEqual("add_perimetrorelacoes" in permissoes, nome == "Gerentes")
            self.assertNotIn("change_revisaocobertura", permissoes)

    def test_backup_e_exportacao_preservam_membros_e_revisoes(self):
        from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
        from inventario.infraestrutura.exportacao import inventario_completo
        p = self.perimetro()
        self.revisar(p)
        colecoes = inventario_completo()["colecoes"]
        self.assertEqual(len(colecoes["membroperimetro"]), 2)
        self.assertEqual(len(colecoes["revisaocobertura"]), 1)
        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode(), SAURON_BACKUP_DESTINO_ADICIONAL=""):
            arquivo = backup_sqlite()
            saida = Path(self.diretorio.name)/"fase5-restaurado.sqlite3"
            restaurar_backup(arquivo, saida)
        with sqlite3.connect(saida) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM inventario_membroperimetro").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT resultado FROM inventario_revisaocobertura").fetchone()[0], "SEM_RELACOES")

    def test_terminal_usa_mesmo_resultado_da_api(self):
        from inventario.cli_menus.cobertura import cobertura
        p = self.perimetro()
        cli = Mock(usuario=self.usuario)
        cli._exigir.return_value = True
        cli._texto.side_effect = ["1", "REDE"]
        cli._inteiro.return_value = p.pk
        cobertura(cli)
        esperado = self.consulta(p)
        self.assertEqual(json.loads(cli.saida.call_args.args[0]), json.loads(json.dumps(esperado, default=str)))

    def test_terminal_conta_desativada_apos_previa_nao_grava_revisao(self):
        from inventario.cli_menus.cobertura import cobertura
        p = self.perimetro()
        cli = Mock(usuario=self.usuario)
        cli._exigir.return_value = True
        cli._inteiro.return_value = p.pk
        cli._ativo.return_value = self.a
        cli._texto.side_effect = ["4", "REDE", "SEM_RELACOES", "Evidência", str(self.hoje), str(self.hoje+timedelta(days=10))]
        def confirmar(_):
            get_user_model().objects.filter(pk=self.usuario.pk).update(is_active=False)
            return True
        cli._confirmar.side_effect = confirmar
        with self.assertRaises(PermissionDenied):
            cobertura(cli)
        self.assertFalse(RevisaoCobertura.objects.exists())
