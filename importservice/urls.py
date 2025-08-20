from django.urls import path, include
from rest_framework import routers
from .views import (
    UploadArquivoView,
    RemoverProdutoView,
    ListarProdutosView,
    ListarHistoricoView,
    ApiRootView,
    RepresentacaoGraficaListCreateView,
    RepresentacaoGraficaDetailView,
    RepresentacaoGraficaBulkUpdateView,
    ProdutoGeoespacialViewSet,
    RepresentacaoGraficaViewSet,
    HistoricoImportacaoExclusaoViewSet
)

# Caso queira usar ViewSets com roteador DRF
router = routers.DefaultRouter()
router.register(r'produtos-geoespaciais', ProdutoGeoespacialViewSet, basename='produtos-geoespaciais')
router.register(r'representacao-grafica', RepresentacaoGraficaViewSet, basename='representacao-grafica')
router.register(r'historico-importacoes', HistoricoImportacaoExclusaoViewSet, basename='historico-importacoes')

urlpatterns = [
    path("", ApiRootView.as_view(), name="api-root"),
    path("importar/", UploadArquivoView.as_view(), name="importar"),
    path("remover/<str:metadata_id>/", RemoverProdutoView.as_view(), name="remover"),
    path("produtos/", ListarProdutosView.as_view(), name="listar_produtos"),
    path("historico/", ListarHistoricoView.as_view(), name="historico"),
    path("representacoes/", RepresentacaoGraficaListCreateView.as_view(), name="representacoes-list"),
    path("representacoes/<int:pk>/", RepresentacaoGraficaDetailView.as_view(), name="representacoes-detail"),
    path("representacoes/bulk-update/", RepresentacaoGraficaBulkUpdateView.as_view(), name="representacoes-bulk-update"),
    # Incluindo todas as rotas de ViewSets via router
    path("api/", include(router.urls)),
]

# Opcional: URLs para Swagger UI
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="API Geodataimporter",
      default_version='v1',
      description="Documentação Swagger para API Geodataimporter",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns += [
    path('swagger(<format>\.json|\.yaml)', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
