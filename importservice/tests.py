from django.test import TestCase

# Create your tests here.
from importservice.models import RepresentacaoGrafica
from importservice import ogr_importer
import os


class RepresentacaoGraficaTestCase(TestCase):
    def setUp(self):
        RepresentacaoGrafica.objects.create(classe="TRA_Trecho_Ferroviario_L", grupo_representacao="Ferrovia")
        RepresentacaoGrafica.objects.create(classe="HID_Trecho_Drenagem_L", grupo_representacao="Rodovia")

    def test_representacao_grafica(self):
        """Animals that can speak are correctly identified"""
        rg = RepresentacaoGrafica.objects.all()
        print(RepresentacaoGrafica.objects.get_dict())
        #self.assertEqual(cat.speak(), 'The cat says "meow"')
    
    def test_importacao(self):
        #RepresentacaoGrafica.objects.create(classe="TRA_Trecho_Ferroviario_L", grupo_representacao="Ferrovia")
        #RepresentacaoGrafica.objects.create(classe="HID_Trecho_Drenagem_L", grupo_representacao="Rodovia")
        nome_banco = ogr_importer.CONFIG_BANCO["dbname"]
        # Cria banco se não existir
        ogr_importer.criar_banco_postgis(nome_banco)
        # Ativa PostGIS no banco
        ogr_importer.ativar_postgis(nome_banco)
        # Monta string de conexão GDAL
        conn_str = "PG: " + ' '.join(f"{k}={v}" for k, v in ogr_importer.CONFIG_BANCO.items())
        ogr_importer.verificar_ou_criar_tabela(ogr_importer.TABELA_GLOBAL, conn_str)

        importar_todos = []
        for root, dirs, files in os.walk(ogr_importer.PASTA_ARQUIVOS):
            for file in files:
                if file.lower().endswith(("zip", "gpkg")):
                    importar_todos.append(os.path.join(root, file))

        ET_EDGV_GROUPS = RepresentacaoGrafica.objects.get_dict()

        for caminho in importar_todos:
            xml_associado = ogr_importer.find_xml_for_file(caminho)
            try:
                ogr_importer.importar_para_tabela(caminho, ogr_importer.TABELA_GLOBAL, xml_associado, ET_EDGV_GROUPS=ET_EDGV_GROUPS)
            except Exception as e:
                ogr_importer.safe_print(f"❌ Erro ao processar '{caminho}': {e}")

        ogr_importer.safe_print("🚀 Processo finalizado.")