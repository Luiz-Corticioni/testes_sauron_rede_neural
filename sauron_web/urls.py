from django.contrib import admin
from django.urls import include, path

handler400 = 'inventario.web.erros.erro_400'
handler403 = 'inventario.web.erros.erro_403'
handler404 = 'inventario.web.erros.erro_404'
handler500 = 'inventario.web.erros.erro_500'

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("inventario.web.urls")),
]
