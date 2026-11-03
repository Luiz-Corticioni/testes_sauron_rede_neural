"""Dados fictícios adicionais, exclusivamente para seed_demo --operacional vazio."""

from datetime import timedelta
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction
from django.utils import timezone

from inventario.models import Incidencia, SnapshotRisco, Software, Vulnerabilidade


def preparar_demo_operacional():
    autor = get_user_model().objects.create(
        username=f"demo_aceitante_{uuid.uuid4().hex[:8]}", is_active=True
    )
    autor.set_unusable_password()  # Conta de cenário não pode autenticar por senha.
    autor.save()
    autor.groups.add(Group.objects.get(name="Gerentes"))
    i = Incidencia.objects.get(pk="INC-0001")
    i.prazo_correcao = timezone.localdate() - timedelta(days=1)
    i.save()
    i = Incidencia.objects.get(pk="INC-0002")
    i.status, i.aceita_por = "ACEITA", autor
    i.justificativa = "SIMULAÇÃO acadêmica de aceite vencido; sem decisão operacional real."
    i.aceita_ate = timezone.localdate() - timedelta(days=1)
    i.save()
    v = Vulnerabilidade.objects.get(pk="VUL-RCE-0001")
    v.kev = True
    v.fonte = "Cenário demonstrativo; KEV simulado"
    v.uso_ransomware = "Unknown"
    v.save()
    # O feed atual não é fingido: emite um evento claramente identificado como demonstração.
    from inventario.aplicacao.operacao import emitir_alerta

    emitir_alerta(
        "KEV",
        Incidencia.objects.get(pk="INC-0001").ativo,
        "demo-kev",
        "SIMULAÇÃO de entrada de CVE no KEV; não representa sincronização real.",
        4,
    )
    Software.objects.create(
        ativo_id="1D00001",
        nome="Log4j (demo)",
        versao="2.14.1",
        fornecedor="Apache",
        cpe23="cpe:2.3:a:apache:log4j:2.14.1:*:*:*:*:*:*:*",
    )
    # Duas amostras artificiais + snapshot real atual permitem demonstrar a derivada.
    for dias, total in [(2, 10), (1, 20)]:
        SnapshotRisco.objects.create(
            ts=timezone.now() - timedelta(days=dias),
            risco_total=total,
            por_ativo={},
            chave=f"DEMO-FICTICIO-{dias}",
            perfil="puro",
        )
    # Depois dos snapshots do seed, demonstra a tendência antes de outras mudanças de estado.
    from inventario.aplicacao.operacao import alertar_tendencia

    transaction.on_commit(alertar_tendencia)
