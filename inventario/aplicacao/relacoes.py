"""Casos de uso compartilhados por web, API e terminal; nenhuma consulta de rede."""
import hashlib
import json
from django.core.exceptions import ValidationError
from inventario.aplicacao.autorizacao import exigir
from django.db import transaction
from django.utils import timezone
from inventario.dominio.grafo_relacoes import GrafoRelacoes, MAX_NOS, MAX_ARESTAS
from inventario.infraestrutura.auditoria import usar_usuario, travar_escrita
from inventario.models import Ativo, RelacaoAtivos, PerimetroRelacoes
from inventario.dominio.cobertura import motivo

LEITURA = ("inventario.view_ativo", "inventario.view_relacaoativos")
CAMPOS = ("origem_id", "destino_id", "tipo", "escopo", "protocolo", "porta", "principal",
          "privilegio", "fonte", "evidencia", "observada_em", "revisar_em", "vigente")
AVISO = ("Alcance estrutural das relações declaradas e no prazo, em uma única camada e escopo. "
         "Não confirma encaminhamento de tráfego, disponibilidade de credenciais, exploração, "
         "comprometimento ou probabilidade. Retirar um vínculo na simulação não altera o inventário.")


def autorizar(usuario, acao=None):
    permissoes = (*LEITURA, f"inventario.{acao}_relacaoativos") if acao else LEITURA
    return exigir(usuario, *permissoes)


def salvar_relacao(dados, usuario, pk=None, versao=None):
    if set(dados) - set(CAMPOS):
        raise ValidationError("Campo de relação não permitido.")
    with transaction.atomic():
        travar_escrita()
        usuario = autorizar(usuario, "change" if pk else "add")
        with usar_usuario(usuario):
            obj = RelacaoAtivos.objects.get(pk=pk) if pk else RelacaoAtivos(criada_por=usuario)
            if pk and obj.atualizado_em.isoformat() != versao:
                raise ValidationError("A relação mudou; recarregue antes de editar.")
            for campo, valor in dados.items():
                setattr(obj, campo, valor)
            obj.atualizada_por = usuario
            obj.save()
            return obj


def carregar_recorte(tipo, escopo, principal=""):
    if tipo not in dict(RelacaoAtivos.TIPOS) or not isinstance(escopo, str) or not escopo.strip() or len(escopo) > 200:
        raise ValueError("Selecione uma camada e informe um escopo exato de até 200 caracteres.")
    if not isinstance(principal, str) or len(principal) > 200 or (tipo == "IDENTIDADE") != bool(principal.strip()):
        raise ValueError("Identidade exige principal exato; as outras camadas não recebem principal.")
    with transaction.atomic():
        perimetro = PerimetroRelacoes.objects.filter(nome=escopo.strip()).first()
        qs = Ativo.objects.exclude(status__in=["INATIVO", "BAIXADO"])
        if perimetro:
            qs = qs.filter(perimetros_declarados__perimetro=perimetro)
        ativos = list(qs.order_by("pk").values("id", "status")[:MAX_NOS+1])
        campos = [f.attname for f in RelacaoAtivos._meta.concrete_fields]
        linhas = list(RelacaoAtivos.objects.filter(tipo=tipo, escopo=escopo.strip(), principal=principal.strip()).order_by("pk").values(*campos, "origem__status", "destino__status")[:MAX_ARESTAS+1])
    if len(ativos) > MAX_NOS or len(linhas) > MAX_ARESTAS:
        raise ValueError("Limite de 10.000 ativos operacionais ou 50.000 relações excedido; revise o dimensionamento deste recorte.")
    return ativos, linhas, perimetro


def analisar_relacoes(usuario, tipo, escopo, origem, destino=None, principal="", remover_relacao=None, remover_ativo=None, limite=50):
    autorizar(usuario)
    if remover_relacao is not None and (type(remover_relacao) is not int or remover_relacao < 1):
        raise ValueError("ID da relação retirada deve ser inteiro positivo.")
    hoje = timezone.localdate()
    # Sem cache: grafo e qualidade usam a mesma seleção e regra de elegibilidade.
    ativos, linhas, perimetro = carregar_recorte(tipo, escopo, principal)
    ids = {a["id"] for a in ativos}
    elegiveis = [a for a in linhas if motivo(a, ids, hoje) == "ELEGIVEL"]
    grafo = GrafoRelacoes(sorted(ids), elegiveis)
    resultado = grafo.analisar(origem, destino, remover_relacao, remover_ativo, limite)
    canonico = json.dumps({"data": hoje, "ativos": ativos, "relacoes": linhas, "perimetro": perimetro.pk if perimetro else None}, sort_keys=True, default=str, ensure_ascii=False)
    resultado.update(tipo=tipo, escopo=escopo.strip(), principal=principal.strip(), data=hoje.isoformat(),
        snapshot_sha256=hashlib.sha256(canonico.encode()).hexdigest(),
        relacoes_no_escopo=len(linhas), excluidas=len(linhas)-len(elegiveis), aviso=AVISO)
    resultado["perimetro_id"] = perimetro.pk if perimetro else None
    # Somente as relações nos caminhos exibidos: detalhes suficientes para conferir as premissas.
    caminhos = [*resultado["itens"], resultado["alvo_base"], resultado["alvo_cenario"]]
    usados = {p["relacao"] for c in caminhos if c for p in c["passos"]}
    referencias = [a for a in elegiveis if a["id"] in usados]
    resultado["evidencias"] = [{k: a[k] for k in ("id", "origem_id", "destino_id", "protocolo", "porta", "principal", "privilegio", "fonte", "evidencia", "observada_em", "revisar_em")}
                               for a in referencias[:200]]
    resultado["evidencias_limitadas"] = len(referencias) > 200
    return resultado
