from django.urls import path
from .views import (
    UploadArquivoView,
    RemoverProdutoView,
    ListarProdutosView,
    ListarHistoricoView,
    ApiRootView
)

urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("importar/", UploadArquivoView.as_view(), name="importar"),
    path("remover/<str:metadata_id>/", RemoverProdutoView.as_view(), name="remover"),
    path("produtos/", ListarProdutosView.as_view(), name="listar_produtos"),
    path("historico/", ListarHistoricoView.as_view(), name="historico"),
]
