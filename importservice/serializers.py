from rest_framework import serializers
from .models import (
    HistoricoImportacaoExclusao,
    ProdutoGeoespacial,
    ProductIndex,
    RepresentacaoGrafica
)


# ========================================
# Serializer para histórico de importações/exclusões
# ========================================
class HistoricoImportacaoExclusaoSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = HistoricoImportacaoExclusao
        fields = '__all__'


# ========================================
# Serializer para produtos geoespaciais
# ========================================
class ProdutoGeoespacialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdutoGeoespacial
        fields = '__all__'


# ========================================
# Serializer para índice de produtos
# ========================================
class ProductIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductIndex
        fields = '__all__'


# ========================================
# Serializer para representação gráfica
# ========================================
class RepresentacaoGraficaSerializer(serializers.ModelSerializer):
    # Exibe o nome do grupo de representação legível
    grupo_representacao_display = serializers.CharField(
        source='get_grupo_representacao_display',
        read_only=True
    )

    class Meta:
        model = RepresentacaoGrafica
        fields = [
            'id',
            'esquema',
            'classe',
            'grupo_representacao',
            'grupo_representacao_display'
        ]
