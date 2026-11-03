"""Única tradução SQL↔objetos puros; reconstrução não grava no banco."""

from copy import deepcopy
from inventario.dominio.equipamentos import criar_equipamento
from inventario.dominio.vulnerabilidades import Dependencia, Incidencia, Vulnerabilidade


def iso(valor):
    return valor.isoformat() if valor else None


class ConversaoAtivo:
    CAMPOS_DOMINIO = (
        "id",
        "id_numerico",
        "nome",
        "hostname",
        "fabricante",
        "modelo",
        "sistema_operacional",
        "versao",
        "responsavel",
        "sala_id",
        "criticidade",
    )
    CAMPOS_ESTADO = (
        "status",
        "alocacao_excepcional_autorizada",
        "justificativa_excecao",
        "autorizado_por_id",
        "contato",
        "confidencialidade",
        "integridade",
        "disponibilidade",
        "exposto_internet",
        "linha_base_saudavel",
        "zona_rede",
        "portas_servicos",
    )

    def para_dominio(self):
        dados = {nome: getattr(self, nome) for nome in self.CAMPOS_DOMINIO}
        estado = {nome: deepcopy(getattr(self, nome)) for nome in self.CAMPOS_ESTADO}
        estado["fim_suporte"] = iso(self.fim_suporte)
        metadados = deepcopy(self.atributos)
        metadados["estado_operacional"] = estado
        dados.update(tipo=self.tipo, ip=self.ip or "", metadados=metadados)
        return criar_equipamento(dados)

    @classmethod
    def de_dominio(cls, objeto):
        dados = {nome: getattr(objeto, nome) for nome in cls.CAMPOS_DOMINIO}
        metadados = deepcopy(objeto.metadados)
        estado = metadados.pop("estado_operacional", {})
        dados.update(tipo=objeto.tipo.value, ip=objeto.ip or None, atributos=metadados)
        for nome in (*cls.CAMPOS_ESTADO, "fim_suporte"):
            if nome in estado:
                dados[nome] = estado[nome]
        if dados.get("fim_suporte"):
            from datetime import date

            dados["fim_suporte"] = date.fromisoformat(dados["fim_suporte"])
        return cls(**dados)


class ConversaoVulnerabilidade:
    CAMPOS_DOMINIO = (
        "id",
        "descricao",
        "categoria",
        "cvss",
        "cve_id",
        "cvss_versao",
        "cvss_vetor",
        "fonte",
        "referencias",
        "kev",
        "uso_ransomware",
        "epss",
    )
    DATAS_DOMINIO = ("publicada_em", "kev_adicionada_em", "kev_prazo", "epss_data")

    def para_dominio(self):
        dados = {nome: deepcopy(getattr(self, nome)) for nome in self.CAMPOS_DOMINIO}
        dados.update({nome: iso(getattr(self, nome)) for nome in self.DATAS_DOMINIO})
        return Vulnerabilidade(**dados)

    @classmethod
    def de_dominio(cls, objeto):
        from datetime import date

        dados = objeto.to_dict()
        dados.pop("severidade")
        for nome in cls.DATAS_DOMINIO:
            dados[nome] = date.fromisoformat(dados[nome]) if dados[nome] else None
        return cls(**dados)


class ConversaoIncidencia:
    CAMPOS_DOMINIO = (
        "id",
        "vulnerabilidade_id",
        "status",
        "versao_afetada",
        "observacoes",
        "aceita_por_id",
        "justificativa",
    )
    DATAS_DOMINIO = ("detectada_em", "prazo_correcao", "aceita_ate")

    def para_dominio(self):
        dados = {nome: getattr(self, nome) for nome in self.CAMPOS_DOMINIO}
        dados.update({nome: iso(getattr(self, nome)) for nome in self.DATAS_DOMINIO})
        return Incidencia(equipamento_id=self.ativo_id, **dados)

    @classmethod
    def de_dominio(cls, objeto):
        from datetime import date

        dados = objeto.to_dict()
        dados["ativo_id"] = dados.pop("equipamento_id")
        for nome in cls.DATAS_DOMINIO:
            dados[nome] = date.fromisoformat(dados[nome]) if dados[nome] else None
        return cls(**dados)


class ConversaoDependencia:
    def para_dominio(self):
        return Dependencia(self.dependente_id, self.fornecedor_id, self.peso, self.descricao)

    @classmethod
    def de_dominio(cls, objeto):
        return cls(**objeto.to_dict())
