"""Representação JSON do inventário, gerada somente sob solicitação explícita."""

from contextlib import contextmanager
import os
from pathlib import Path

from django.db import transaction

from inventario.infraestrutura.repositorio_json import RepositorioJSON
from inventario.models import Ativo, Dependencia, Incidencia, Vulnerabilidade


@contextmanager
def trava_exportacao(diretorio: Path):
    """Serializa exportadores entre processos no Linux e no Windows."""
    diretorio.mkdir(parents=True, exist_ok=True)
    with (diretorio / ".exportacao.lock").open("a+b") as arquivo:
        if os.name == "nt":
            import msvcrt

            if arquivo.tell() == 0:
                arquivo.write(b"0")
                arquivo.flush()
            arquivo.seek(0)
            msvcrt.locking(arquivo.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                arquivo.seek(0)
                msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)


def colecoes_json(using="default") -> dict[str, list[dict]]:
    """Mantém IDs, tipos polimórficos, status e vínculos por chave estrangeira."""
    modelos = {
        "equipamentos.json": Ativo,
        "vulnerabilidades.json": Vulnerabilidade,
        "incidencias.json": Incidencia,
        "dependencias.json": Dependencia,
    }
    return {
        nome: [
            objeto.para_dominio().to_dict() for objeto in modelo.objects.using(using).order_by("pk")
        ]
        for nome, modelo in modelos.items()
    }


def exportar_inventario_json(saida, using="default") -> dict[str, int]:
    """Lê um snapshot consistente e substitui atomicamente cada array JSON."""
    with trava_exportacao(Path(saida)):
        with transaction.atomic(using=using):
            colecoes = colecoes_json(using)
        for nome, itens in colecoes.items():
            RepositorioJSON(Path(saida) / nome).salvar_todos(itens)
    return {nome: len(itens) for nome, itens in colecoes.items()}


def inventario_completo(using="default"):
    """Snapshot dos cadastros e evidências. Não substitui backup cifrado restaurável."""
    from django.apps import apps
    from django.utils import timezone
    from inventario.infraestrutura.auditoria import dados_objeto
    # Coleções explicitamente revisadas; novos modelos não entram por acidente.
    permitidos = {"ativo", "sala", "software", "vulnerabilidade", "incidencia", "dependencia",
                  "relacaoativos", "perimetrorelacoes", "membroperimetro", "revisaocobertura", "incidente", "certificadodigital", "historicoincidencia", "snapshotrisco",
                  "anticorpo", "tolerancia", "sugestaoimune", "alerta", "observacaoepss", "avaliacaossvc", "documentoinventario", "itemsbom", "achadocomponente", "declaracaovex"}
    colecoes = {
        modelo._meta.model_name: [dados_objeto(objeto) for objeto in
                                 modelo.objects.using(using).order_by("pk").iterator()]
        for modelo in apps.get_app_config("inventario").get_models()
        if modelo._meta.model_name in permitidos
    }
    colecoes["fontes_achados"] = list(apps.get_model("inventario", "AchadoComponente").fontes.through.objects.using(using).values())
    return {"formato": "sauron.inventario/v2", "exportado_em": timezone.now().isoformat(),
            "colecoes": colecoes}
