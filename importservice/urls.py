from .views import acesso
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import Importar_Arquivo_ViewSet
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'arquivos', Importar_Arquivo_ViewSet)

urlpatterns = [
    path("hello/", acesso),
    path('', include(router.urls)),
]