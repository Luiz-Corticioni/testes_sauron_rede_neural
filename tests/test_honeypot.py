import json
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from inventario.aplicacao.honeypot import salvar_sensor, importar_eventos, validar_lote
from inventario.models import Alerta, EventoHoneypot, SensorHoneypot, RegistroAuditoria
from .base import BancoTeste


def evento(id_="exemplo-1", tipo="CONEXAO", ip="192.0.2.10"):
    return {"id": id_, "observado_em": "2026-11-13T12:00:00Z", "origem_ip": ip, "tipo": tipo}


def arquivo(*eventos):
    return json.dumps(list(eventos)).encode()


class HoneypotTeste(BancoTeste):
    def setUp(self):
        super().setUp()
        self.sensor = salvar_sensor(SensorHoneypot(nome="Isca laboratório", responsavel="Equipe", ativo=self.a), self.usuario)

    def test_importa_agrega_audita_e_nao_altera_risco(self):
        antes = self.a.incidencia_set.count()
        resultado = importar_eventos(self.sensor.pk, arquivo(evento(), evento("exemplo-2", "LOGIN_FALHOU")), self.usuario)
        self.assertEqual(resultado, {"recebidos": 2, "novos": 2, "duplicados": 0})
        self.assertEqual(EventoHoneypot.objects.count(), 2)
        self.assertEqual(Alerta.objects.filter(tipo="HONEYPOT", ativo=self.a).count(), 1)
        self.assertIn("Demonstração", Alerta.objects.get(tipo="HONEYPOT").mensagem)
        self.assertEqual(self.a.incidencia_set.count(), antes)
        auditoria = RegistroAuditoria.objects.filter(acao="IMPORTAR", entidade="SensorHoneypot").latest("id")
        self.assertEqual(auditoria.usuario_id, self.usuario.pk)
        self.assertNotIn("192.0.2.10", str(auditoria.detalhes))

    def test_repetir_lote_e_idempotente(self):
        importar_eventos(self.sensor.pk, arquivo(evento()), self.usuario)
        resultado = importar_eventos(self.sensor.pk, arquivo(evento(), evento()), self.usuario)
        self.assertEqual(resultado["novos"], 0)
        self.assertEqual(resultado["duplicados"], 2)
        self.assertEqual(EventoHoneypot.objects.count(), 1)
        self.assertEqual(Alerta.objects.filter(tipo="HONEYPOT").count(), 1)

    def test_id_existente_com_outros_dados_rejeita_lote_inteiro(self):
        importar_eventos(self.sensor.pk, arquivo(evento()), self.usuario)
        with self.assertRaises(ValidationError):
            importar_eventos(self.sensor.pk, arquivo(evento("novo"), evento(ip="192.0.2.99")), self.usuario)
        self.assertEqual(EventoHoneypot.objects.count(), 1)

    def test_rejeita_campos_sensiveis_dados_invalidos_e_limites(self):
        ruim = evento() | {"password": "nao registrar"}
        exemplos = [arquivo(ruim), arquivo(evento(ip="não é IP")), arquivo(evento(ip="fe80::1%eth0")), arquivo(evento(tipo="INVALIDO")),
                    arquivo(evento() | {"observado_em": "2026-11-13T12:00:00"}),
                    b"[" + b" " * (1024 * 1024), b"{}"]
        for conteudo in exemplos:
            with self.subTest(conteudo=conteudo[:70]), self.assertRaises(ValidationError):
                validar_lote(conteudo)
        self.assertFalse(EventoHoneypot.objects.exists())

    def test_sensor_desabilitado_e_usuario_sem_permissao(self):
        sem = get_user_model().objects.create_user("sem-sensor")
        with self.assertRaises(PermissionDenied):
            importar_eventos(self.sensor.pk, arquivo(evento()), sem)
        self.sensor.habilitado = False
        self.sensor.save()
        with self.assertRaises(ValidationError):
            importar_eventos(self.sensor.pk, arquivo(evento()), self.usuario)
        self.assertFalse(EventoHoneypot.objects.exists())

    def test_fluxo_web_upload_e_escopo_de_permissoes(self):
        conteudo = SimpleUploadedFile("eventos.json", arquivo(evento()), content_type="application/json")
        resposta = self.client.post(f"/honeypot/{self.sensor.pk}/importar/", {"arquivo": conteudo})
        self.assertEqual(resposta.status_code, 302)
        resposta = self.client.get("/honeypot/")
        self.assertContains(resposta, "192.0.2.10")
        sem = get_user_model().objects.create_user("somente-leitor")
        sem.user_permissions.add(Permission.objects.get(content_type__app_label="inventario", codename="view_ativo"))
        self.autenticar(sem)
        self.assertEqual(self.client.get("/honeypot/").status_code, 403)
        self.assertEqual(self.client.post(f"/honeypot/{self.sensor.pk}/importar/").status_code, 403)

    def test_mfa_e_necessario_para_consultar(self):
        self.client.logout()
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get("/honeypot/").url, "/mfa/")

    def test_configuracao_grupos_nao_concede_leitura_a_operadores_e_auditores(self):
        from django.contrib.auth.models import Group
        from django.core.management import call_command
        call_command("configurar_grupos", verbosity=0)
        for nome in ("Operadores", "Auditores"):
            permissoes = Group.objects.get(name=nome).permissions.values_list("codename", flat=True)
            self.assertNotIn("view_eventohoneypot", permissoes)
            self.assertNotIn("view_sensorhoneypot", permissoes)
        self.assertTrue(Group.objects.get(name="Gerentes").permissions.filter(codename="view_eventohoneypot").exists())

    def test_edicao_desabilita_sensor_sem_apagar_eventos(self):
        importar_eventos(self.sensor.pk, arquivo(evento()), self.usuario)
        self.sensor.habilitado = False
        salvar_sensor(self.sensor, self.usuario)
        self.assertEqual(EventoHoneypot.objects.count(), 1)
        with self.assertRaises(ValidationError):
            importar_eventos(self.sensor.pk, arquivo(evento("novo")), self.usuario)

    def test_ambiente_nao_reclassifica_eventos_antigos(self):
        importar_eventos(self.sensor.pk, arquivo(evento()), self.usuario)
        self.sensor.ambiente = "OPERACIONAL"
        with self.assertRaises(ValidationError):
            salvar_sensor(self.sensor, self.usuario)
        self.sensor.refresh_from_db()
        self.assertEqual(self.sensor.ambiente, "DEMONSTRACAO")

    def test_recusa_mais_de_500_eventos(self):
        with self.assertRaises(ValidationError):
            validar_lote(json.dumps([evento(str(n)) for n in range(501)]).encode())

    def test_ativo_nao_reclassifica_o_historico(self):
        importar_eventos(self.sensor.pk, arquivo(evento()), self.usuario)
        self.sensor.ativo = self.b
        with self.assertRaises(ValidationError):
            salvar_sensor(self.sensor, self.usuario)
        self.sensor.refresh_from_db()
        self.assertEqual(self.sensor.ativo_id, self.a.pk)

    def test_cadastro_e_desativacao_pela_interface(self):
        resposta = self.client.post("/honeypot/novo/", {
            "nome": "Demonstração UI", "localizacao": "Rede de teste", "responsavel": "SOC",
            "ativo": self.a.pk, "ambiente": "DEMONSTRACAO", "habilitado": "on"})
        self.assertEqual(resposta.status_code, 302)
        sensor = SensorHoneypot.objects.get(nome="Demonstração UI")
        resposta = self.client.post(f"/honeypot/{sensor.pk}/editar/", {
            "nome": sensor.nome, "localizacao": "Rede de teste", "responsavel": "SOC",
            "ativo": self.a.pk, "ambiente": "DEMONSTRACAO"})
        self.assertEqual(resposta.status_code, 302)
        sensor.refresh_from_db()
        self.assertFalse(sensor.habilitado)

    def test_backup_anterior_a_migracao_ignora_apenas_as_tabelas_ainda_nao_criadas(self):
        from cryptography.fernet import Fernet
        from django.db import connection
        from django.db.migrations.recorder import MigrationRecorder
        from django.test import override_settings
        from unittest.mock import patch
        from inventario.infraestrutura.backup import backup_sqlite

        tabelas = connection.introspection.table_names()
        anteriores = {k: v for k, v in MigrationRecorder(connection).applied_migrations().items()
                      if k != ("inventario", "0029_alter_alerta_tipo_sensorhoneypot_eventohoneypot")}
        sem_tabelas = [t for t in tabelas if t not in {"inventario_sensorhoneypot", "inventario_eventohoneypot"}]
        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode(), SAURON_BACKUP_DESTINO_ADICIONAL=""):
            with patch.object(connection.introspection, "table_names", return_value=sem_tabelas), \
                 patch.object(MigrationRecorder, "applied_migrations", return_value=anteriores):
                self.assertTrue(backup_sqlite().exists())
            with patch.object(connection.introspection, "table_names", return_value=sem_tabelas):
                with self.assertRaisesMessage(ValueError, "Tabela ausente"):
                    backup_sqlite()
