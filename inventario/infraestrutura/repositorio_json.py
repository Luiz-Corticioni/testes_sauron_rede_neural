from __future__ import annotations

from abc import ABC, abstractmethod
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile


class Repositorio(ABC):
    @abstractmethod
    def listar(self) -> list[dict]: ...

    @abstractmethod
    def salvar_todos(self, itens: list[dict]) -> None: ...


class RepositorioJSON(Repositorio):
    """Persiste uma lista de objetos JSON com escrita atômica."""

    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)

    def listar(self) -> list[dict]:
        if not self.caminho.exists():
            return []
        with self.caminho.open(encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if not isinstance(dados, list):
            raise ValueError(f"{self.caminho} deve conter um array JSON.")
        return dados

    def salvar_todos(self, itens: list[dict]) -> None:
        if not isinstance(itens, list):
            raise TypeError("A raiz do arquivo deve ser uma lista.")
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
