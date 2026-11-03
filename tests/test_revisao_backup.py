from pathlib import Path
import subprocess
from unittest.mock import patch
from django.conf import settings
from django.test import override_settings
from cryptography.fernet import Fernet
from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
from .base import BancoTeste


class PublicacaoBackup(BancoTeste):
    def test_interrupcao_nao_deixa_banco_parcial(self):
        destino = settings.DATA_DIR / "interrompido.sqlite3"
        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode()):
            arquivo = backup_sqlite()
            with patch(
                "inventario.infraestrutura.backup.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "migrate"),
            ):
                with self.assertRaisesMessage(ValueError, "interrompida"):
                    restaurar_backup(arquivo, destino)
        self.assertFalse(destino.exists())
        self.assertFalse(list(destino.parent.glob("restauracao-*")))

    def test_destino_criado_durante_carga_nao_e_sobrescrito(self):
        destino = settings.DATA_DIR / "concorrente.sqlite3"

        def comando(*args, **kwargs):
            Path(kwargs["env"]["SAURON_DB_PATH"]).touch()
            destino.write_bytes(b"banco de outro processo")

        with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode()):
            arquivo = backup_sqlite()
            with patch("inventario.infraestrutura.backup.subprocess.run", side_effect=comando):
                with self.assertRaisesMessage(ValueError, "passou a existir"):
                    restaurar_backup(arquivo, destino)
        self.assertEqual(destino.read_bytes(), b"banco de outro processo")

    def test_backup_pre_migracao_ignora_somente_tabela_nova_esperada(self):
        import json
        from django.db import connection
        from django.db.migrations.recorder import MigrationRecorder

        tabelas = connection.introspection.table_names()
        aplicadas = MigrationRecorder(connection).applied_migrations()
        antigas = {
            k: v for k, v in aplicadas.items() if k != ("inventario", "0020_dispositivo_email")
        }
        chave = Fernet.generate_key()
        with override_settings(SAURON_BACKUP_KEY=chave.decode()):
            with (
                patch.object(
                    connection.introspection,
                    "table_names",
                    return_value=[t for t in tabelas if t != "inventario_dispositivoemail"],
                ),
                patch.object(MigrationRecorder, "applied_migrations", return_value=antigas),
            ):
                arquivo = backup_sqlite()
            itens = json.loads(Fernet(chave).decrypt(arquivo.read_bytes()))
            self.assertFalse(any(i["model"] == "inventario.dispositivoemail" for i in itens))
            self.assertTrue(any(i["model"] == "auth.user" for i in itens))
            with patch.object(
                connection.introspection,
                "table_names",
                return_value=[t for t in tabelas if t != "inventario_dispositivoemail"],
            ):
                with self.assertRaisesMessage(ValueError, "Tabela ausente"):
                    backup_sqlite()

    def test_backup_descarta_codigos_temporarios_e_sessoes(self):
        import json
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        from datetime import timedelta
        from inventario.models import DispositivoEmail

        Session.objects.create(
            session_key="ativa", session_data="", expire_date=timezone.now() + timedelta(days=1)
        )
        dispositivo, _ = DispositivoEmail.objects.get_or_create(
            user=self.usuario, defaults={"name": "E-mail"}
        )
        dispositivo.codigo_hash = "a" * 64
        dispositivo.nonce = "b" * 64
        dispositivo.pode_adotar = True
        dispositivo.expira_em = timezone.now() + timedelta(minutes=5)
        dispositivo.save()
        chave = Fernet.generate_key()
        with override_settings(SAURON_BACKUP_KEY=chave.decode()):
            itens = json.loads(Fernet(chave).decrypt(backup_sqlite().read_bytes()))
        self.assertFalse(any(i["model"] == "sessions.session" for i in itens))
        salvo = next(
            i
            for i in itens
            if i["model"] == "inventario.dispositivoemail" and i["pk"] == dispositivo.pk
        )
        self.assertEqual(salvo["fields"]["codigo_hash"], "")
        self.assertEqual(salvo["fields"]["nonce"], "")
        self.assertFalse(salvo["fields"]["pode_adotar"])
        self.assertIsNone(salvo["fields"]["expira_em"])
        dispositivo.refresh_from_db()
        self.assertTrue(dispositivo.codigo_hash)  # O banco em uso não é alterado pelo backup.
