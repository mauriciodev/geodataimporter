from django.shortcuts import render
from django.http import HttpResponse
import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response

def current_datetime(request):
    now = datetime.datetime.now()
    # Obtém o valor do parâmetro "nome" enviado na query string
    name = request.GET.get('nome', 'IME')  # valor padrão: "Visitante"
    html = '<html lang="en"><body>Boa tarde,  %s.</body></html>' % name
    return HttpResponse(html)

# Create your views here.
@api_view(["GET"])
def acesso(request):
    return Response({"mensagem": "Hello, world!"})
