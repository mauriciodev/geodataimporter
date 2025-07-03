from osgeo import ogr
import json
import os

fname = "old_examples/estacoes.gpkg"

# Caminho absoluto com base no local do script
base_dir = os.path.dirname(__file__)
fname = os.path.join(base_dir, "old_examples", "estacoes.gpkg")

datasource = ogr.Open(fname)

# Entrada do serviço REST: arquivo vetorial, nome da modelagem (com a versão)
# Entradas opcionais: metadata_id, data_do_produto e escala

metadata_id = ''
for layer in datasource:
    print(layer.GetName())
    for feature in layer:
        print(feature)
        feature_json = feature.ExportToJson()
        feature_dict = json.loads(feature_json)
        json_attributes = json.dumps(feature_dict["properties"])
        geom = feature.GetGeometryRef()
        print("Geometria:", geom)
        print("JSON", json_attributes)
        print("Classe:", layer.GetName())
        if metadata_id == '':
            metadata_id = fname
        print("Metadata_id:", metadata_id)
