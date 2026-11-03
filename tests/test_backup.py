
import sqlite3
from contextlib import closing
from datetime import timedelta
from django.utils import timezone
from django.test import override_settings
from cryptography.fernet import Fernet
from inventario.infraestrutura.backup import backup_sqlite, restaurar_backup
from .base import BancoTeste


class R17(BancoTeste):
    def test_backup_cifrado_e_restauracao_limpa(self):
        from django.conf import settings
        from django.contrib.sessions.models import Session
        Session.objects.create(session_key="expirada",session_data="",expire_date=timezone.now()-timedelta(days=1))
        chave=Fernet.generate_key().decode()
        destino=settings.DATA_DIR/"restaurado.sqlite3"
        with override_settings(SAURON_BACKUP_KEY=chave, SAURON_BACKUP_DESTINO_ADICIONAL=settings.DATA_DIR/"copia"):
            backup=backup_sqlite()
            self.assertNotIn(b"VUL-RCE",backup.read_bytes())
            restaurar_backup(backup,destino)
            with closing(sqlite3.connect(destino)) as banco:
                self.assertEqual(banco.execute("SELECT count(*) FROM inventario_ativo").fetchone()[0],2)
                self.assertEqual(banco.execute("SELECT count(*) FROM django_session WHERE session_key='expirada'").fetchone()[0],0)
            with self.assertRaises(ValueError):
                restaurar_backup(backup,destino)
            with override_settings(SAURON_BACKUP_KEY=Fernet.generate_key().decode()), self.assertRaises(ValueError):
                restaurar_backup(backup,settings.DATA_DIR/"chave-errada.sqlite3")

