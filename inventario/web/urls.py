from django.urls import path
from django.contrib.auth.views import LogoutView
from inventario.seguranca import LoginProtegido, proteger

from inventario.web import views
from inventario.web import api_v1
from inventario.web import views_documentos
from inventario.web import views_relacoes
from inventario.web import views_cobertura
from inventario.aplicacao.cobertura import LEITURA as LEITURA_COBERTURA
from inventario.aplicacao.relacoes import LEITURA as LEITURA_RELACOES
from inventario.aplicacao.documentos import LEITURA as LEITURA_DOCUMENTOS
from inventario.web import views_ssvc
from inventario.aplicacao.ssvc import PERMISSOES_LEITURA
from inventario.web import views_epss
from inventario.web import views_imune
from inventario.web import views_cadastros
from inventario.web import views_visualizacoes
from inventario.web import views_comparacao
from inventario.web import views_cves
from inventario.web import views_vinculos
from inventario.web import views_analises, views_operacionais
from functools import partial
from inventario.web.views_mfa import verificar_mfa

PERMISSOES_RISCO = (
    "inventario.view_ativo",
    "inventario.view_vulnerabilidade",
    "inventario.view_incidencia",
    "inventario.view_dependencia",
)


urlpatterns = [
    path("api/v1/ativos/", api_v1.ativos, name="api_v1_ativos"),
    path("api/v1/vulnerabilidades/<str:pk>/ativos/", api_v1.ativos_afetados, name="api_v1_ativos_afetados"),
    path("epss/atualizar/", proteger(views_analises.atualizar_epss, *PERMISSOES_RISCO, "inventario.change_vulnerabilidade"), name="atualizar_epss"),
    path("qualidade-relacoes/", proteger(views_cobertura.painel, *LEITURA_COBERTURA), name="qualidade_relacoes"),
    path("api/qualidade-relacoes/", proteger(views_cobertura.api, *LEITURA_COBERTURA), name="api_qualidade_relacoes"),
    path("perimetros/novo/", proteger(views_cobertura.perimetro_form, *LEITURA_COBERTURA), name="criar_perimetrorelacoes"),
    path("perimetros/<int:pk>/editar/", proteger(views_cobertura.perimetro_form, *LEITURA_COBERTURA), name="editar_perimetrorelacoes"),
    path("cobertura/revisar/", proteger(views_cobertura.revisar, *LEITURA_COBERTURA), name="revisar_cobertura"),
    path("cobertura/<int:pk>/", proteger(views_cobertura.detalhe, *LEITURA_COBERTURA), name="revisao_cobertura"),
    path("relacoes/", proteger(views_relacoes.lista, *LEITURA_RELACOES), name="relacoes"),
    path("relacoes/nova/", proteger(views_relacoes.formulario, *LEITURA_RELACOES), name="criar_relacaoativos"),
    path("relacoes/<int:pk>/", proteger(views_relacoes.detalhe, *LEITURA_RELACOES), name="relacao"),
    path("relacoes/<int:pk>/editar/", proteger(views_relacoes.formulario, *LEITURA_RELACOES), name="editar_relacaoativos"),
    path("grafo-relacoes/", proteger(views_relacoes.painel, *LEITURA_RELACOES), name="grafo_relacoes"),
    path("api/grafo-relacoes/", proteger(views_relacoes.api, *LEITURA_RELACOES), name="api_grafo_relacoes"),
    path("documentos/", proteger(views_documentos.lista, *LEITURA_DOCUMENTOS), name="documentos"),
    path("documentos/<int:pk>/", proteger(views_documentos.detalhe, *LEITURA_DOCUMENTOS), name="documento"),
    path("documentos/<int:pk>/baixar/", proteger(views_documentos.baixar, *LEITURA_DOCUMENTOS), name="baixar_documento"),
    path("incidencias/<str:pk>/ssvc/", proteger(views_ssvc.painel, *PERMISSOES_LEITURA), name="ssvc_incidencia"),
    path("vulnerabilidades/<str:pk>/epss/", proteger(views_epss.historico, "inventario.view_vulnerabilidade"), name="historico_epss"),
    path("comparar-cvss/", proteger(views_comparacao.comparacao, "inventario.view_vulnerabilidade"), name="comparar_cvss"),
    path("guia/", views_comparacao.guia, name="guia"),
    path("incidencias/<str:pk>/revisar/", proteger(views_operacionais.decidir_pendencia_web, "inventario.change_incidencia"), name="decidir_pendencia"),
    path("mfa/", verificar_mfa, name="mfa"),
    path("montecarlo/", proteger(views_analises.montecarlo, *PERMISSOES_RISCO), name="montecarlo"),
    path("api/montecarlo/", proteger(views_analises.api_montecarlo, *PERMISSOES_RISCO), name="api_montecarlo"),
    path("api/impacto/", proteger(views_analises.api_impacto,
         "inventario.view_ativo", "inventario.view_dependencia"), name="api_impacto"),
    path("api/risco/diagnostico/", proteger(views_analises.api_diagnostico,
         *PERMISSOES_RISCO), name="api_diagnostico_linear"),
    path('api/cves/sugestoes/', proteger(views_cves.api_sugestoes_cves, 'inventario.view_vulnerabilidade'), name='api_sugestoes_cves'),
    path('api/cves/consultar/', proteger(views_cves.api_consultar_cves, 'inventario.view_vulnerabilidade'), name='api_consultar_cves'),
    path("mapa/", proteger(views_visualizacoes.mapa, *PERMISSOES_RISCO), name="mapa"),
    path("matrizes/", proteger(views_visualizacoes.matrizes, *PERMISSOES_RISCO), name="matrizes"),
    path(
        "prioridades/",
        proteger(views_visualizacoes.prioridades, *PERMISSOES_RISCO),
        name="prioridades",
    ),
    path(
        "imune/",
        proteger(
            views_imune.painel,
            "inventario.view_sugestaoimune",
            "inventario.view_anticorpo",
            "inventario.view_tolerancia",
        ),
        name="imune",
    ),
    path(
        "imune/ciclo/",
        proteger(views_imune.ciclo, "inventario.change_incidencia"),
        name="imune_ciclo",
    ),
    path(
        "imune/<int:pk>/decidir/",
        proteger(views_imune.decidir, "inventario.decidir_sugestao_imune"),
        name="imune_decidir",
    ),
    path(
        "alertas/",
        proteger(
            views.alertas,
            "inventario.view_alerta",
            "inventario.view_incidencia",
            "inventario.view_ativo",
            "inventario.view_vulnerabilidade",
        ),
        name="alertas",
    ),
    path(
        "alertas/<int:pk>/reconhecer/",
        proteger(views.reconhecer_alerta_web, "inventario.reconhecer_alerta"),
        name="reconhecer_alerta",
    ),
    path(
        "incidencias/<str:pk>/decisao/",
        proteger(views.status_incidencia_web, "inventario.change_incidencia"),
        name="status_incidencia_web",
    ),
    path("software/", proteger(views.software, "inventario.view_software"), name="software"),
    path("importar/", proteger(views.importar_ativos, "inventario.add_ativo"), name="importar"),
    path("exportar/<str:colecao>.csv", views.exportar_colecao_csv, name="exportar_colecao_csv"),
    path("entrar/", LoginProtegido.as_view(), name="entrar"),
    path("sair/", LogoutView.as_view(), name="sair"),
    path(
        "auditoria/",
        proteger(views.auditoria, "inventario.view_registroauditoria"),
        name="auditoria",
    ),
    path(
        "api/auditoria/verificar/",
        proteger(views.api_verificar_auditoria, "inventario.view_registroauditoria"),
        name="api_verificar_auditoria",
    ),
    path(
        "incidencias/<str:pk>/status/",
        proteger(views.alterar_status_incidencia, "inventario.change_incidencia"),
        name="alterar_status_incidencia",
    ),
    path("", proteger(views.dashboard, *PERMISSOES_RISCO), name="dashboard"),
    path("ativos/", proteger(views.listar_ativos, "inventario.view_ativo"), name="ativos"),
    path("ativos/novo/", proteger(views.criar_ativo, "inventario.add_ativo"), name="criar_ativo"),
    path("ativos/<str:pk>/vulnerabilidades/vincular/", proteger(
        views_vinculos.vincular, "inventario.view_ativo", "inventario.view_vulnerabilidade",
        "inventario.add_incidencia"), name="vincular_vulnerabilidade_ativo"),
    path("ativos/<str:pk>/vulnerabilidades/cadastrar/", proteger(
        views_vinculos.cadastrar, "inventario.view_ativo", "inventario.view_vulnerabilidade",
        "inventario.add_vulnerabilidade", "inventario.add_incidencia"), name="cadastrar_vulnerabilidade_ativo"),
    path("ativos/<str:pk>/dependencias/nova/", proteger(
        views_vinculos.dependencia, "inventario.view_ativo", "inventario.add_dependencia"),
        name="dependencia_ativo"),
    path(
        "ativos/<str:pk>/",
        proteger(views.detalhe_ativo, "inventario.view_ativo"),
        name="detalhe_ativo",
    ),
    path(
        "vulnerabilidades/",
        proteger(views.listar_vulnerabilidades, "inventario.view_vulnerabilidade"),
        name="vulnerabilidades",
    ),
    path(
        "vulnerabilidades/nova/",
        proteger(views.criar_vulnerabilidade, "inventario.add_vulnerabilidade"),
        name="criar_vulnerabilidade",
    ),
    path("modo-euler/", proteger(views.modo_euler, *PERMISSOES_RISCO), name="modo_euler"),
    path("cves/", proteger(views.menu_cves, "inventario.view_vulnerabilidade"), name="cves"),
    path(
        "exportar/ativos.csv",
        proteger(views.exportar_ativos_csv, "inventario.view_ativo"),
        name="exportar_ativos_csv",
    ),
    path("api/saude/", views.api_saude, name="api_saude"),
    path("api/saude/detalhe/", proteger(views.api_saude_detalhe, "inventario.view_registroauditoria"), name="api_saude_detalhe"),
    path("api/ativos/", proteger(views.api_ativos, "inventario.view_ativo"), name="api_ativos"),
    path("api/risco/", proteger(views.api_risco, *PERMISSOES_RISCO), name="api_risco"),
    path(
        "api/risco/simular/",
        proteger(views.api_simular_risco, *PERMISSOES_RISCO),
        name="api_simular_risco",
    ),
    path(
        "api/risco/historico/",
        proteger(views.api_historico_risco, *PERMISSOES_RISCO),
        name="api_historico_risco",
    ),
    path("api/cvss/", proteger(views.api_cvss, "inventario.view_vulnerabilidade"), name="api_cvss"),
    path(
        "api/cves/kev/", proteger(views.api_kev, "inventario.view_vulnerabilidade"), name="api_kev"
    ),
    path(
        "api/cves/<str:cve_id>/",
        proteger(views.api_nvd, "inventario.view_vulnerabilidade"),
        name="api_nvd",
    ),
]

# Todas as mutações exigem permissão própria; GET só apresenta formulário/confirmação.
for cadastro, (modelo, _, destino, _) in views_cadastros.CADASTROS.items():
    for acao, permissao, handler, sufixo in (
        ("editar", "change", views_cadastros.formulario, "editar/"),
        ("remover", "delete", views_cadastros.exclusao, "remover/"),
    ):
        urlpatterns.append(
            path(
                f"{destino}/<str:pk>/{sufixo}",
                proteger(partial(handler, cadastro=cadastro), f"inventario.{permissao}_{cadastro}"),
                name=f"{acao}_{cadastro}",
            )
        )
    if cadastro in {"incidencia", "dependencia", "sala"}:
        urlpatterns.extend(
            [
                path(
                    f"{destino}/",
                    proteger(
                        partial(views_cadastros.listar_relacoes, cadastro=cadastro),
                        f"inventario.view_{cadastro}",
                    ),
                    name=destino,
                ),
                path(
                    f"{destino}/novo/",
                    proteger(
                        partial(views_cadastros.formulario, cadastro=cadastro),
                        f"inventario.add_{cadastro}",
                    ),
                    name=f"criar_{cadastro}",
                ),
            ]
        )
