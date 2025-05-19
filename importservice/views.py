from django.shortcuts import render
from django.http import HttpResponse
import datetime


def current_datetime(request):
    now = datetime.datetime.now()
    # Obtém o valor do parâmetro "nome" enviado na query string
    name = request.GET.get('nome', 'IME')  # valor padrão: "Visitante"
    html = '<html lang="en"><body>Boa tarde,  %s.</body></html>' % name
    return HttpResponse(html)

# Create your views here.
