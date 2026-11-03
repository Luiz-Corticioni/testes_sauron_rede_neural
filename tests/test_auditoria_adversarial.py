
from django.db import connection, transaction, DatabaseError
from django.test import override_settings
from inventario.infraestrutura.auditoria import registrar_evento, verificar_cadeia, calcular_hash
from inventario.models import RegistroAuditoria
from .base import BancoTeste


@override_settings(SAURON_AUDIT_HMAC_KEY="chave-de-teste-sem-valor-operacional")
class R15(BancoTeste):
    def test_hmac_e_imutabilidade_sql(self):
        r=registrar_evento("TESTE","Teste","1")
        self.assertEqual(r.cadeia_versao,2)
        with self.assertRaises(DatabaseError), transaction.atomic():
            RegistroAuditoria.objects.filter(pk=r.pk).update(entidade_id="adulterado")
        with self.assertRaises(DatabaseError), transaction.atomic():
            RegistroAuditoria.objects.filter(pk=r.pk).delete()
        r.entidade_id="alterado"
        original=calcular_hash(r)
        with override_settings(SAURON_AUDIT_HMAC_KEY="outra-chave"):
            self.assertNotEqual(calcular_hash(r),original)

    def test_ancora_detecta_truncamento_e_assinatura(self):
        from django.conf import settings
        from inventario.infraestrutura.ancoras import ancorar
        destino=settings.DATA_DIR/"ancoras.jsonl"
        with override_settings(SAURON_AUDIT_ANCHOR_PATH=destino):
            r=registrar_evento("TESTE","Teste","ancorado")
            ancorar()
            self.assertTrue(verificar_cadeia()["integra"])
            with connection.cursor() as c:
                c.execute("DROP TRIGGER auditoria_sem_delete")
                c.execute("DELETE FROM inventario_registroauditoria WHERE id=%s",[r.pk])
            self.assertFalse(verificar_cadeia()["integra"])

    def test_recomputar_sem_chave_falha(self):
        from inventario.infraestrutura.auditoria import calcular_hash as calcular
        r=registrar_evento("TESTE","Teste","1")
        with connection.cursor() as c:
            c.execute("DROP TRIGGER auditoria_sem_update")
            r.entidade_id="adulterado"
            with override_settings(SAURON_AUDIT_HMAC_KEY="chave-atacante"):
                falso=calcular(r)
            c.execute("UPDATE inventario_registroauditoria SET entidade_id=%s, hash=%s WHERE id=%s",
                      ["adulterado",falso,r.pk])
        self.assertFalse(verificar_cadeia()["integra"])

