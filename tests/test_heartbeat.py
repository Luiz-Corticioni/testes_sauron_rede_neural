
import json
from datetime import timedelta
from django.utils import timezone
from .base import BancoTeste


class R18(BancoTeste):
    def test_heartbeat_expirado_e_ausente_falham(self):
        from inventario.infraestrutura.heartbeat import verificar_heartbeat
        from django.conf import settings
        caminho=settings.DATA_DIR/"ultima_rotina.json"
        self.assertFalse(verificar_heartbeat(caminho,3600))
        caminho.write_text(json.dumps({"finalizada_em":(timezone.now()-timedelta(seconds=7201)).isoformat()}))
        self.assertFalse(verificar_heartbeat(caminho,3600))
        caminho.write_text(json.dumps({"finalizada_em":timezone.now().isoformat()}))
        self.assertTrue(verificar_heartbeat(caminho,3600))

