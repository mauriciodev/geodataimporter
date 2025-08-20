from rest_framework import serializers
from .models import (
    HistoricoImportacaoExclusao,
    ProdutoGeoespacial,
    product_index,
    RepresentacaoGrafica
)


class HistoricoImportacaoExclusaoSerializer(serializers.ModelSerializer):
    usuario = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = HistoricoImportacaoExclusao
        fields = '__all__'


class ProdutoGeoespacialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProdutoGeoespacial
        fields = '__all__'


class ProductIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = product_index
        fields = '__all__'

class RepresentacaoGrafica(serializers.ModelSerializer):
    class Meta:
        model = RepresentacaoGrafica
        fields = '__all__'
