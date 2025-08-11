from django.db import models
from django.conf import settings
from django.contrib.gis.db import models as geomodels
import uuid

# Tabela original de índices dos produtos
class product_index(models.Model):
    area = geomodels.MultiPolygonField()
    metadataid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    date = models.DateField()
    scale = models.IntegerField()
    file_path = models.FilePathField(path='.')  # caminho relativo, pode ser ajustado conforme o servidor

    def __str__(self):
        return f"{self.metadataid}: {self.file_path}"


# Tabela de histórico de adições e exclusões de produtos
class HistoricoImportacaoExclusao(models.Model):
    ACAO_CHOICES = [
        ('adicionado', 'Adicionado'),
        ('removido', 'Removido'),
    ]

    metadata_id = models.CharField(max_length=256)
    classe = models.CharField(max_length=256, null=True, blank=True)
    acao = models.CharField(max_length=10, choices=ACAO_CHOICES)
    data_evento = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    detalhes = models.TextField(null=True, blank=True)  # para mensagens adicionais, erros etc

    def __str__(self):
        return f"{self.acao.capitalize()} {self.metadata_id} ({self.classe or 'todas classes'}) em {self.data_evento.strftime('%d/%m/%Y %H:%M:%S')}"


# Informações sobre os arquivos importados (camada administrativa, complementar à tabela vetorial do PostGIS)
class ProdutoGeoespacial(models.Model):
    metadata_id = models.CharField(max_length=256, unique=True)
    nome_arquivo = models.CharField(max_length=256)
    data_do_produto = models.DateField(null=True, blank=True)
    data_importacao = models.DateTimeField(auto_now_add=True)
    esquema = models.CharField(max_length=256, null=True, blank=True)
    escala = models.CharField(max_length=64, null=True, blank=True)
    area_mapeada = geomodels.PolygonField(null=True, blank=True, srid=4326)

    def __str__(self):
        return f"{self.metadata_id} ({self.data_do_produto})"

class RepresentacaoGrafica(models.Model):
    esquema = models.CharField(max_length=256, null=True, blank=True)
    classe = models.CharField(max_length=256, null=True, blank=True)
    representacao_grafica = models.CharField(max_length=256, null=True, blank=True)

    def __str__(self):
        return f"{self.classe} ({self.esquema})"
