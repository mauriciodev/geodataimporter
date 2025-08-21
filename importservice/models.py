from django.db import models
from django.conf import settings
from django.contrib.gis.db import models as geomodels
import uuid

# ========================================
# Índice de produtos geoespaciais
# ========================================
class ProductIndex(models.Model):
    area = geomodels.MultiPolygonField()
    metadataid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=True)
    date = models.DateField()
    scale = models.IntegerField()
    file_path = models.FilePathField(path='.')  # caminho relativo, pode ser ajustado conforme o servidor

    def __str__(self):
        return f"{self.metadataid}: {self.file_path}"


# ========================================
# Histórico de importação/exclusão
# ========================================
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
    detalhes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.acao.capitalize()} {self.metadata_id} ({self.classe or 'todas classes'}) em {self.data_evento.strftime('%d/%m/%Y %H:%M:%S')}"


# ========================================
# Produtos geoespaciais
# ========================================
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


# ========================================
# Representação gráfica das classes
# ========================================

class RepresentacaoGraficaManager(models.Manager):
    def get_dict(self):
        queryset = super().get_queryset()
        product_dict = {item['classe']: item['grupo_representacao'] for item in queryset.values('classe', 'grupo_representacao')}
        return product_dict
    
class RepresentacaoGrafica(models.Model):

    esquema = models.CharField(max_length=256)
    classe = models.CharField(max_length=256)
    grupo_representacao = models.CharField(
        max_length=50, default='outros'
    )

    class Meta:
        unique_together = ['esquema', 'classe']
        verbose_name = 'Representação Gráfica'
        verbose_name_plural = 'Representações Gráficas'

    """def save(self, *args, **kwargs):
        # Preenche automaticamente o grupo gráfico pelo mapeamento
        if not self.grupo_representacao or self.grupo_representacao == 'outros':
            self.grupo_representacao = self.EDGV_GRUPO_MAP.get(self.classe, 'outros')
        super().save(*args, **kwargs)"""
    objects = RepresentacaoGraficaManager()

    def __str__(self):
        return f"{self.classe} ({self.esquema}) - {self.grupo_representacao}"
