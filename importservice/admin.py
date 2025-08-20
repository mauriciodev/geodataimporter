from django.contrib import admin
from importservice.models import (
    RepresentacaoGrafica,
    HistoricoImportacaoExclusao,
    ProdutoGeoespacial,
    ProductIndex
)

# -----------------------------
# Representacao Grafica Admin
# -----------------------------
@admin.register(RepresentacaoGrafica)
class RepresentacaoGraficaAdmin(admin.ModelAdmin):
    list_display = ['esquema', 'classe', 'grupo_representacao']
    list_filter = ['esquema', 'grupo_representacao']
    search_fields = ['classe', 'esquema']
    ordering = ['esquema', 'classe']

# -----------------------------
# Historico Importacao/Exclusao Admin
# -----------------------------
@admin.register(HistoricoImportacaoExclusao)
class HistoricoImportacaoExclusaoAdmin(admin.ModelAdmin):
    list_display = ['metadata_id', 'classe', 'acao', 'usuario', 'data_evento']
    list_filter = ['acao', 'usuario', 'data_evento']
    search_fields = ['metadata_id', 'classe', 'detalhes']
    ordering = ['-data_evento']

# -----------------------------
# Produto Geoespacial Admin
# -----------------------------
@admin.register(ProdutoGeoespacial)
class ProdutoGeoespacialAdmin(admin.ModelAdmin):
    list_display = ['metadata_id', 'nome_arquivo', 'data_do_produto', 'data_importacao', 'esquema', 'escala']
    list_filter = ['esquema', 'escala', 'data_importacao']
    search_fields = ['metadata_id', 'nome_arquivo', 'esquema']
    ordering = ['-data_importacao']

# -----------------------------
# Product Index Admin
# -----------------------------
@admin.register(ProductIndex)
class ProductIndexAdmin(admin.ModelAdmin):
    list_display = ['metadataid', 'file_path', 'date', 'scale']
    list_filter = ['date', 'scale']
    search_fields = ['metadataid', 'file_path']
    ordering = ['-date']
