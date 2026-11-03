"""Menu de ativos: adaptador de terminal."""

from __future__ import annotations
from inventario.aplicacao.servicos import salvar_cadastro, remover_cadastro, sala_exige_autorizacao

from django.core.exceptions import ValidationError
from inventario.dominio.enums import TipoEquipamento
from inventario.models import Ativo, Incidencia, Sala
from inventario.cli_menus.comum import Cor, menu_seguro


class AtivosMenu:

    @menu_seguro("view_ativo")
    def menu_ativos(self):
        while True:
            opcao = self._submenu(
                "ATIVOS DE TI",
                [
                    ("1", "Listar"),
                    ("2", "Consultar detalhes"),
                    ("3", "Cadastrar"),
                    ("4", "Atualizar"),
                    ("5", "Remover"),
                ],
            )
            if opcao == "0":
                return
            {
                "1": self.listar_ativos,
                "2": self.detalhar_ativo,
                "3": self.criar_ativo,
                "4": self.atualizar_ativo,
                "5": self.remover_ativo,
            }.get(opcao, lambda: self._falha("Opção inválida."))()
            self._pausa()

    def listar_ativos(self):
        ativos = Ativo.objects.select_related("sala")
        self._tabela(
            ["ID nº", "Código", "Hostname", "Tipo", "Fabricante", "Sala", "Crit.", "Status"],
            [
                [
                    a.id_numerico,
                    a.id,
                    a.hostname,
                    a.get_tipo_display(),
                    f"{a.fabricante} {a.modelo}".strip(),
                    a.sala_id,
                    a.criticidade,
                    a.status,
                ]
                for a in ativos
            ],
            [6, 8, 25, 22, 22, 14, 5, 12],
        )

    def detalhar_ativo(self):
        a = self._ativo()
        self.saida(f"\n{Cor.titulo(a.hostname)}  (ID {a.id_numerico} · código {a.id})")
        for nome, valor in [
            ("Tipo", a.get_tipo_display()),
            ("Nome", a.nome),
            ("IP", a.ip),
            ("Fabricante", f"{a.fabricante} {a.modelo}"),
            ("Sistema", f"{a.sistema_operacional} {a.versao}"),
            ("Responsável", a.responsavel),
            ("Sala", a.sala),
            ("Criticidade", a.criticidade),
            ("Status", a.status),
            ("Fim de suporte", a.fim_suporte),
        ]:
            self.saida(f"  {nome:<17} {valor or '—'}")
        incs = Incidencia.objects.filter(ativo=a).select_related("vulnerabilidade")
        self.saida(Cor.destaque("\nVulnerabilidades vinculadas"))
        self._tabela(
            ["Incidência", "Vulnerabilidade", "CVSS", "Status"],
            [
                [
                    i.id,
                    i.vulnerabilidade.cve_id or i.vulnerabilidade_id,
                    i.vulnerabilidade.cvss,
                    i.status,
                ]
                for i in incs
            ],
        )

    def _escolher_tipo(self, padrao: str | None = None) -> str:
        for t in TipoEquipamento:
            self.saida(f"  {t.codigo} - {t.rotulo}")
        escolha = self._texto("Tipo", padrao=padrao)
        return TipoEquipamento(escolha).value

    def _escolher_sala(self, padrao: str | None = None) -> Sala:
        salas = list(Sala.objects.all())
        self._tabela(["ID", "Nome", "Categoria"], [[s.id, s.nome, s.categoria] for s in salas])
        if not salas:
            raise ValueError("Cadastre uma sala antes do ativo.")
        return Sala.objects.get(pk=self._texto("ID da sala", padrao=padrao).upper())

    def criar_ativo(self):
        if not self._exigir("inventario.add_ativo"):
            return
        tipo = self._escolher_tipo()
        sala = self._escolher_sala()
        a = Ativo(
            tipo=tipo,
            nome=self._texto("Nome amigável"),
            hostname=self._texto("Hostname (vazio = automático)", permitir_vazio=True),
            fabricante=self._texto("Fabricante"),
            modelo=self._texto("Modelo", permitir_vazio=True),
            ip=self._texto("IPv4", permitir_vazio=True) or None,
            sistema_operacional=self._texto("Sistema operacional", permitir_vazio=True),
            versao=self._texto("Versão", permitir_vazio=True),
            responsavel=self._texto("Responsável"),
            sala=sala,
            criticidade=self._inteiro("Criticidade", 1, 4, 1),
            status=self._texto("Status", padrao="ATIVO"),
            fim_suporte=self._data("Fim de suporte", True),
        )
        if sala_exige_autorizacao(sala, tipo):
            self.saida(
                Cor.aviso("[AVISO] Sala restrita ou tipo incompatível: exige autorização especial.")
            )
            if not self.usuario.has_perm(
                "inventario.autorizar_alocacao_excepcional"
            ) or not self._confirmar("Autorizar excepcionalmente?"):
                raise ValidationError("Cadastro cancelado: sala incompatível.")
            a.alocacao_excepcional_autorizada = True
            a.justificativa_excecao = self._texto("Justificativa")
            a.autorizado_por = self.usuario
        salvar_cadastro(a, self.usuario)
        self._ok(f"Ativo ID {a.id_numerico}, código {a.id}, criado; hostname {a.hostname}.")

    def atualizar_ativo(self):
        if not self._exigir("inventario.change_ativo"):
            return
        a = self._ativo()
        campos = {
            "1": ("nome", "Nome"),
            "2": ("responsavel", "Responsável"),
            "3": ("ip", "IPv4"),
            "4": ("status", "Status"),
            "5": ("criticidade", "Criticidade"),
            "6": ("sala", "Sala"),
            "7": ("fim_suporte", "Fim de suporte"),
        }
        for k, (_, rotulo) in campos.items():
            self.saida(f"  {k} - {rotulo}")
        escolha = self._texto("Campo")
        if escolha not in campos:
            raise ValueError("Campo inválido.")
        campo, rotulo = campos[escolha]
        _anterior = str(getattr(a, campo))
        if campo == "criticidade":
            valor = self._inteiro("Novo valor", 1, 4)
        elif campo == "sala":
            valor = self._escolher_sala(a.sala_id)
        elif campo == "fim_suporte":
            valor = self._data("Nova data", True)
        else:
            valor = self._texto("Novo valor", permitir_vazio=campo == "ip") or None
        setattr(a, campo, valor)
        if campo == "sala" and sala_exige_autorizacao(valor, a.tipo):
            self.saida(Cor.aviso("[AVISO] O tipo do ativo não é compatível com a nova sala."))
            if not self.usuario.has_perm(
                "inventario.autorizar_alocacao_excepcional"
            ) or not self._confirmar("Autorizar excepcionalmente?"):
                raise ValidationError("Alteração cancelada: sala incompatível.")
            a.alocacao_excepcional_autorizada = True
            a.justificativa_excecao = self._texto("Justificativa")
            a.autorizado_por = self.usuario
        salvar_cadastro(a, self.usuario)
        self._ok(f"{rotulo} atualizado.")

    def remover_ativo(self):
        if not self._exigir("inventario.delete_ativo"):
            return
        a = self._ativo()
        if not self._confirmar(f"Remover definitivamente {a.hostname} e seus vínculos?"):
            return
        aid, _host = (a.id, a.hostname)
        remover_cadastro(a, self.usuario)
        self._ok(f"Ativo {aid} removido.")
