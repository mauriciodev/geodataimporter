from django.urls import path
from .views import (
    ApiRootView,
    ListarHistoricoView,
    ListarProdutosView,
    UploadArquivoView,
    RemoverProdutoView,
    RepresentacaoGraficaBulkUpdateView,
)

urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("historico/", ListarHistoricoView.as_view(), name="historico"),
    path("produtos/", ListarProdutosView.as_view(), name="produtos"),
    path("importar/", UploadArquivoView.as_view(), name="importar"),
    path("remover/<str:metadata_id>/", RemoverProdutoView.as_view(), name="remover"),
    path("representacoes/bulk-update/", RepresentacaoGraficaBulkUpdateView.as_view(), name="representacoes-bulk-update"),
]
