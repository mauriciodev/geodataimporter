from django.shortcuts import render
from django.http import HttpResponse
import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import viewsets
from .models import Importar_Arquivo
from .serializers import Importar_Arquivo_Serializer
from rest_framework.parsers import MultiPartParser, FormParser

def current_datetime(request):
    now = datetime.datetime.now()
    # Obtém o valor do parâmetro "nome" enviado na query string
    name = request.GET.get('nome', 'IME')  # valor padrão: "Visitante"
    html = '<html lang="en"><body>Boa tarde,  %s.</body></html>' % name
    return HttpResponse(html)

# Criar um ponto de acesso no DRF (hello world). Responder um objeto json como rest.
@api_view(["GET"])
def acesso(request):
    return Response({"mensagem": "Hello, world!"})

# Enviar arquivos por drf
class Importar_Arquivo_ViewSet(viewsets.ModelViewSet):
    queryset = Importar_Arquivo.objects.all()
    serializer_class = Importar_Arquivo_Serializer
    parser_classes = [MultiPartParser, FormParser]