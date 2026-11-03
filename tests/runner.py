"""Falha se um teste tentar usar sockets; integrações devem fornecer mocks."""
from unittest.mock import patch
from django.test.runner import DiscoverRunner


class SemRedeRunner(DiscoverRunner):
    def setup_test_environment(self, **kwargs):
        super().setup_test_environment(**kwargs)
        self.patches = [patch("socket.socket.connect", side_effect=AssertionError("Rede proibida em testes")),
                        patch("socket.socket.connect_ex", side_effect=AssertionError("Rede proibida em testes"))]
        for p in self.patches:
            p.start()

    def teardown_test_environment(self, **kwargs):
        for p in reversed(self.patches):
            p.stop()
        super().teardown_test_environment(**kwargs)

