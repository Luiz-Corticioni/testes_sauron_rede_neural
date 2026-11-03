import json
from io import StringIO
from django.core.exceptions import ValidationError
from django.core.management import call_command, CommandError
from inventario.models import Vulnerabilidade
from .base import BancoTeste


class AuditoriaNotas(BancoTeste):
    def test_modelo_recusa_nota_nao_finita_antes_do_banco(self):
        for nota in (float("nan"), float("inf"), float("-inf"), 5.25):
            self.v.cvss = nota
            with self.subTest(nota=nota), self.assertRaises(ValidationError):
                self.v.full_clean()

    def test_comando_confere_cadastros_sem_modificar(self):
        saida = StringIO()
        call_command("auditar_cvss", json=True, stdout=saida)
        r = json.loads(saida.getvalue())
        self.assertEqual(r["verificados"], 2)
        self.assertEqual(r["base31_conferida"], 1)
        self.assertEqual(r["sem_vetor31"], 1)
        self.assertEqual(r["divergencias"], [])
        # Um registro legado pode conter nota diferente do vetor. A auditoria detecta,
        # sem substituir a avaliação do responsável ou gravar uma correção automática.
        Vulnerabilidade.objects.filter(pk=self.v.pk).update(cvss=8.1)
        saida = StringIO()
        with self.assertRaises(CommandError):
            call_command("auditar_cvss", json=True, stdout=saida)
        r = json.loads(saida.getvalue())
        self.assertEqual(r["divergencias"][0]["id"], self.v.pk)
        self.v.refresh_from_db()
        self.assertEqual(self.v.cvss, 8.1)
