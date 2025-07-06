from rest_framework import serializers
from .models import Importar_Arquivo

class Importar_Arquivo_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Importar_Arquivo
        fields = '__all__'
        read_only_fields = ['data_upload']
