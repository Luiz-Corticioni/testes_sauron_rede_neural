from django.apps import AppConfig


class InventarioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventario"
    verbose_name = "Sauron — Inventário de Cibersegurança"

    def ready(self):
        from inventario.aplicacao.servicos import conectar_sinais

        conectar_sinais()
        from inventario.infraestrutura import conexoes as conexoes
