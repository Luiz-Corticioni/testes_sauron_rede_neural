from django.conf import settings
from django.db import connection
from django.test import override_settings
from inventario.infraestrutura.ancoras import verificar_ancoras, ancorar
from inventario.infraestrutura.auditoria import verificar_cadeia
from inventario.models import RegistroAuditoria
from .base import BancoTeste


class AuditoriaRevisada(BancoTeste):
    def test_producao_exige_ancora_e_arquivo_vazio_falha(self):
        caminho = settings.DATA_DIR / "ancoras.jsonl"
        with override_settings(SAURON_AUDIT_ANCHOR_PATH=caminho, SAURON_EXIGIR_ANCORA=True):
            self.assertFalse(verificar_ancoras()[0])
            caminho.touch()
            self.assertFalse(verificar_ancoras()[0])
            ancorar()
            self.assertTrue(verificar_ancoras()[0])
            caminho.write_text('{"assinatura": 12}\n', encoding="utf-8")
            self.assertFalse(verificar_ancoras()[0])

    def test_versao_adulterada_retorna_falha_sem_excecao(self):
        pk = RegistroAuditoria.objects.first().pk
        with connection.cursor() as cursor:
            cursor.execute("DROP TRIGGER auditoria_sem_update")
            cursor.execute("UPDATE inventario_registroauditoria SET cadeia_versao=99 WHERE id=%s", [pk])
        resultado = verificar_cadeia(verificar_ancora=False)
        self.assertFalse(resultado["integra"])
        self.assertEqual(resultado["primeiro_elo_quebrado"], pk)
