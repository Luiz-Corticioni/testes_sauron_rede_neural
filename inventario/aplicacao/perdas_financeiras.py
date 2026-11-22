"""Perdas declaradas e ajuste heurístico, sem supor representatividade."""
from django.db import transaction
from django.utils import timezone
import numpy as np

from inventario.aplicacao.autorizacao import exigir
from inventario.infraestrutura.auditoria import registrar_evento, travar_escrita, usar_usuario
from inventario.models import Incidente, PerdaFinanceira

LEITURA = ("inventario.view_ativo", "inventario.view_incidente", "inventario.view_perdafinanceira")
ESCRITA = (*LEITURA, "inventario.add_perdafinanceira")
MINIMO = 10
LIMITE = 5000


@transaction.atomic
def registrar(usuario, incidente, categoria, natureza, valor, data, origem):
    travar_escrita()
    usuario = exigir(usuario, *ESCRITA)
    incidente = Incidente.objects.get(pk=incidente.pk)
    objeto = PerdaFinanceira(incidente=incidente, categoria=categoria, natureza=natureza, valor=valor, data=data,
                             origem=origem, registrado_por=usuario)
    objeto.full_clean()
    with usar_usuario(usuario):
        objeto.save()
        registrar_evento("REGISTRAR_PERDA", "PerdaFinanceira", str(objeto.pk), {"categoria": categoria, "natureza": natureza})
    return objeto


def calibrar(usuario, custos):
    exigir(usuario, *LEITURA)
    selecionadas = list(PerdaFinanceira.objects.filter(natureza="REAL", data__lte=timezone.localdate(), incidente__encerrado_em__isnull=False)
                        .order_by("-data", "-pk").values_list("categoria", "valor")[:LIMITE+1])
    if len(selecionadas) > LIMITE:
        return custos, {"calibrado": False, "motivo": "Mais de 5000 registros; defina um recorte antes de calibrar.", "categorias": []}
    custos_ajustados, categorias = dict(custos), []
    for categoria in "CIA":
        valores = [float(valor) for tipo, valor in selecionadas if tipo == categoria]
        item = {"categoria": categoria, "observacoes": len(valores), "calibrado": False}
        if len(valores) >= MINIMO:
            baixo, mediana, alto = map(float, np.percentile(valores, [10, 50, 90]))
            if baixo < mediana < alto:
                custos_ajustados[categoria] = (baixo, mediana, alto)
                item.update(calibrado=True, faixa=[baixo, mediana, alto])
            else:
                item["motivo"] = "Percentis não formam faixa PERT estritamente crescente."
        else:
            item["motivo"] = f"Menos de {MINIMO} perdas observadas nesta categoria."
        categorias.append(item)
    return custos_ajustados, {"calibrado": any(x["calibrado"] for x in categorias), "categorias": categorias,
        "metodo": "P10/P50/P90 como mínimo/moda aproximada/máximo; ajuste heurístico não comprova representatividade."}
