from __future__ import annotations

from abc import ABC, abstractmethod
from copy import deepcopy
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


class Repositorio(ABC):
    @abstractmethod
    def listar(self) -> list[dict]: ...

    @abstractmethod
    def salvar_todos(self, itens: list[dict]) -> None: ...


def validar_itens(itens):
    if not isinstance(itens, list) or any(not isinstance(item, dict) for item in itens):
        raise ValueError("A coleção deve ser um array JSON de objetos.")


def _constante_invalida(valor):
    raise ValueError(f"Constante JSON inválida: {valor}.")


class RepositorioMemoria(Repositorio):
    """Alternativa transitória para testes e demonstrações, sem acesso ao disco."""

    def __init__(self):
        self._itens = []

    def listar(self) -> list[dict]:
        return deepcopy(self._itens)

    def salvar_todos(self, itens: list[dict]) -> None:
        validar_itens(itens)
        # O mesmo contrato de serialização impede que memória aceite valores que
        # o repositório JSON não conseguiria gravar.
        self._itens = json.loads(json.dumps(itens, allow_nan=False))


class RepositorioJSON(Repositorio):
    """Persiste uma lista de objetos JSON com escrita atômica."""

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)

    def listar(self) -> list[dict]:
        if not self.caminho.exists():
            return []
        with self.caminho.open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo, parse_constant=_constante_invalida)
        validar_itens(dados)
        return dados

    def salvar_todos(self, itens: list[dict]) -> None:
        validar_itens(itens)
        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        temporario_path = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                delete=False,
                dir=self.caminho.parent,
                prefix=f".{self.caminho.name}.",
                suffix=".tmp",
            ) as temporario:
                temporario_path = Path(temporario.name)
                json.dump(itens, temporario, ensure_ascii=False, indent=2, allow_nan=False)
                temporario.flush()
                os.fsync(temporario.fileno())
            temporario_path.replace(self.caminho)
        finally:
            if temporario_path is not None:
                temporario_path.unlink(missing_ok=True)

    def adicionar(self, item: dict, campo_id: str = "id") -> None:
        itens = self.listar()
        if any(existente.get(campo_id) == item.get(campo_id) for existente in itens):
            raise ValueError(f"Já existe um item com {campo_id}={item.get(campo_id)!r}.")
        itens.append(item)
        self.salvar_todos(itens)
