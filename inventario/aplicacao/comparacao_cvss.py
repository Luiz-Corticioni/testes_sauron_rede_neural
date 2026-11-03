"""Consulta explícita à NVD; comparação não altera notas nem decisões do inventário."""

from django.conf import settings
from inventario.dominio.autocomplete import normalizar_cve
from inventario.matematica.cvss import CalculadoraCVSS31
from inventario.dominio.comparacao_cvss import comparar_notas
from inventario.infraestrutura.cve_client import NvdClient, IntegracaoCVEError


def comparar(cve_id="", vetor_local="", atualizar=False, origem_local=None):
    if vetor_local:
        CalculadoraCVSS31.calcular(vetor_local)  # Falha antes da rede se a entrada é inválida.
    cliente = NvdClient(settings.NVD_API_KEY, settings.DATA_DIR / "cache" / "nvd")
    cve_id = normalizar_cve(cve_id) if cve_id else ""
    if cve_id:
        cliente._caminho(cve_id)  # Valida antes de qualquer acesso à rede.
    cve = {"id": cve_id}
    consulta = {"origem": "sem consulta NVD", "consultado_em": None, "expirado": False, "erro": ""}
    avisos = []
    if cve_id:
        if atualizar:
            try:
                cliente.atualizar(cve_id, forcar=True)
                consulta["origem"] = "NVD pela internet"
            except (IntegracaoCVEError, OSError) as erro:
                consulta["erro"] = str(erro)
                avisos.append(
                    "Não foi possível atualizar a NVD. Os dados locais, quando disponíveis, serão identificados como cache."
                )
        try:
            registro = cliente.registro_cache(cve_id)
            cve = registro.pop("cve")
            consulta.update(registro)
            if consulta["origem"] != "NVD pela internet":
                consulta["origem"] = "cache NVD"
            if consulta["expirado"]:
                avisos.append(
                    "Cache NVD expirado (mais de 24 horas); atualize antes de uma decisão operacional."
                )
        except IntegracaoCVEError as erro:
            consulta["origem"] = "NVD indisponível"
            consulta["erro"] = consulta["erro"] or str(erro)
            avisos.append(str(erro))
    kwargs = {"origem_local": origem_local} if origem_local else {}
    resultado = comparar_notas(cve, vetor_local, **kwargs)
    resultado["avisos"] = avisos + resultado["avisos"]
    resultado["consulta"] = consulta
    resultado["url_nvd"] = f"https://nvd.nist.gov/vuln/detail/{cve_id}" if cve_id else ""
    resultado["alterada_na_nvd"] = str(cve.get("lastModified", ""))[:40]
    return resultado
