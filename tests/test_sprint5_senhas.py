"""Regressões da migração transparente de hashes de senha."""

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.test import TestCase


class SenhasArgon2(TestCase):
    def test_senhas_iguais_possuem_sais_distintos(self):
        primeiro = make_password("uma frase de teste forte")
        segundo = make_password("uma frase de teste forte")
        self.assertTrue(primeiro.startswith("argon2$argon2id$"))
        self.assertNotEqual(primeiro, segundo)
        self.assertTrue(check_password("uma frase de teste forte", primeiro))
        self.assertFalse(check_password("senha incorreta", primeiro))

    def test_hash_anterior_e_atualizado_ao_verificar(self):
        usuario = get_user_model().objects.create(username="sprint5-antigo")
        usuario.password = make_password("senha antiga segura", hasher="pbkdf2_sha256")
        usuario.save(update_fields=["password"])
        self.assertTrue(usuario.check_password("senha antiga segura"))
        usuario.refresh_from_db()
        self.assertTrue(usuario.password.startswith("argon2$argon2id$"))
        self.assertFalse(usuario.check_password("senha incorreta"))
