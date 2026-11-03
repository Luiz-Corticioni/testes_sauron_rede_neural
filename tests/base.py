"""Inventário mínimo e isolamento de arquivos/BD para toda a suíte."""
from pathlib import Path
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from inventario.models import Ativo, Sala, Vulnerabilidade, Incidencia, Dependencia


class BancoTeste(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.diretorio = TemporaryDirectory(prefix="sauron-testes-")
        cls.configuracao = override_settings(
            DATA_DIR=Path(cls.diretorio.name),
            SAURON_AUDIT_ANCHOR_PATH=Path(cls.diretorio.name)/"ancoras-auditoria.jsonl",
            SAURON_EXIGIR_ANCORA=False,
            CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
            STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                      "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}},
            ALLOWED_HOSTS=["testserver", "localhost"],
        )
        cls.configuracao.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.configuracao.disable()
        cls.diretorio.cleanup()

    def setUp(self):
        from inventario.infraestrutura.auditoria import definir_usuario
        # Uma sessão CLI não pode contaminar o ator da próxima transação de teste.
        definir_usuario(None)
        self.addCleanup(definir_usuario, None)
        cache.clear()
        self.usuario = get_user_model().objects.create_superuser("teste", "teste@example.org", "senha-teste-123")
        self.autenticar(self.usuario)
        self.sala = Sala.objects.create(id="SALA-TESTE", nome="Laboratório")
        self.a = Ativo.objects.create(tipo="1", nome="Servidor", fabricante="Dell", sala=self.sala,
                                     responsavel="Equipe", exposto_internet=True)
        self.b = Ativo.objects.create(tipo="1", nome="Estação", fabricante="Dell", sala=self.sala,
                                     responsavel="Equipe", criticidade=3)
        self.v = Vulnerabilidade.objects.create(id="VUL-RCE-0001", descricao="Exemplo", categoria="RCE",
            cve_id="CVE-2021-44228", cvss=10, kev=True,
            cvss_vetor="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H")
        self.w = Vulnerabilidade.objects.create(id="VUL-DOS-0002", descricao="Exemplo DOS", categoria="DOS", cvss=5.3)
        self.i = Incidencia.objects.create(id="INC-0001", ativo=self.a, vulnerabilidade=self.v)
        Incidencia.objects.create(id="INC-0002", ativo=self.b, vulnerabilidade=self.w)
        self.dep = Dependencia.objects.create(dependente=self.b, fornecedor=self.a, peso=.2)

    def autenticar(self, usuario, cliente=None):
        cliente = cliente or self.client
        from django_otp.plugins.otp_totp.models import TOTPDevice
        from django.utils import timezone
        cliente.force_login(usuario)
        dispositivo, _ = TOTPDevice.objects.get_or_create(user=usuario, name="Fixture", defaults={"confirmed":True})
        sessao=cliente.session
        sessao["otp_device_id"]=dispositivo.persistent_id
        sessao["sauron_reauth_em"]=timezone.now().timestamp()
        sessao.save()
