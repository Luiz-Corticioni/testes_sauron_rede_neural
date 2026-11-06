"""Consultas apenas de leitura; parâmetros são vinculados pelo adaptador do Django."""

from django.db import connection


def incidencias_por_ativo(limiar=0):
    # LEFT JOIN conserva ativos sem incidências; o filtro está no JOIN, não no WHERE.
    sql = """
        SELECT a.id, a.nome, COUNT(v.id), COALESCE(SUM(v.cvss), 0)
        FROM inventario_ativo a
        LEFT JOIN inventario_incidencia i ON i.ativo_id = a.id
          AND i.status IN (%s, %s, %s)
        LEFT JOIN inventario_vulnerabilidade v ON v.id = i.vulnerabilidade_id
        GROUP BY a.id, a.nome
        HAVING COALESCE(SUM(v.cvss), 0) >= %s
        ORDER BY COALESCE(SUM(v.cvss), 0) DESC, a.id
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, ["ABERTA", "TRATAMENTO", "ACEITA", limiar])
        return [{"id": row[0], "nome": row[1], "incidencias": row[2], "soma_cvss": row[3]}
                for row in cursor.fetchall()]
