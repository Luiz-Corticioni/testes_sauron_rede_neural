"""Catálogo didático independente do ORM; não substitui o banco da aplicação web."""

from inventario.dominio.equipamentos import Equipamento


def por_nome(ativo):
    return ativo.nome.casefold(), ativo.id


def por_tipo(ativo):
    return ativo.tipo.value, ativo.nome.casefold(), ativo.id


class CatalogoEducacional:
    """A mesma operação recebe um repositório e uma estratégia de ordenação."""

    def __init__(self, repositorio):
        self.repositorio = repositorio

    def cadastrar(self, ativo):
        registros = self.repositorio.listar()
        if any(item.get("id") == ativo.id for item in registros):
            raise ValueError("Já existe um ativo com esse identificador.")
        registros.append(ativo.to_dict())
        self.repositorio.salvar_todos(registros)

    def listar(self, estrategia=por_nome):
        return sorted((Equipamento.from_dict(item) for item in self.repositorio.listar()),
                      key=estrategia)
