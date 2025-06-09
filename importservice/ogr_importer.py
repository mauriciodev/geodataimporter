import os
import json
import uuid
import xml.etree.ElementTree as ET
#import psycopg2
from osgeo import ogr

ogr.UseExceptions()

# Configurações
CONFIG_BASE = {
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5433",
}
CONFIG_BANCO = {**CONFIG_BASE, "dbname": "pfc2025"}
TABELA_GLOBAL = "importacao_geometrias"
PASTA_ARQUIVOS = r"C:\\Users\\gabri\\OneDrive\\Área de Trabalho\\Estudos\\Eng Cartografica\\5.1\\PFC\\arquivos"

def safe_print(msg):
    print(msg, flush=True)

def extrair_edgv_com_versao_oficial(xml_path, namespaces):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        title = root.find('.//gmd:MD_FeatureCatalogueDescription/gmd:featureCatalogueCitation/gmd:CI_Citation/gmd:title/gco:CharacterString', namespaces)
        edition = root.find('.//gmd:MD_FeatureCatalogueDescription/gmd:featureCatalogueCitation/gmd:CI_Citation/gmd:edition/gco:CharacterString', namespaces)
        edition_date = root.find('.//gmd:MD_FeatureCatalogueDescription/gmd:featureCatalogueCitation/gmd:CI_Citation/gmd:editionDate/gco:Date', namespaces)
        
        schema_name = f"{title.text} {edition.text} {edition_date.text}"

        # Se não achou versão oficial, só retorna EDGV
        return schema_name

    except Exception as e:
        print(f"Erro ao processar XML (extrair_edgv_com_versao_oficial): {e}")
        return None

def extract_metadata_from_xml(arquivo_xml):
    escala = data_do_produto = esquema = metadata_id = None
    if not arquivo_xml or not os.path.exists(arquivo_xml):
        metadata_id = arquivo_xml
        return escala, data_do_produto, esquema, metadata_id
    try:
        tree = ET.parse(arquivo_xml)
        ns = {
            'gmd': "http://www.isotc211.org/2005/gmd",
            'gco': "http://www.isotc211.org/2005/gco"
        }

        escala_elem = tree.find('.//gmd:equivalentScale//gco:Integer', ns)
        if escala_elem is not None and escala_elem.text:
            escala = f"1:{escala_elem.text.strip()}"

        data_elem = tree.find('.//gmd:CI_Date/gmd:date/gco:Date', ns)
        if data_elem is not None and data_elem.text:
            data_do_produto = data_elem.text.strip()

        file_id_elem = tree.find('.//gmd:fileIdentifier//gco:CharacterString', ns)
        if file_id_elem is not None and file_id_elem.text:
            metadata_id = file_id_elem.text.strip()

        # Extrai esquema usando a função nova
        esquema = extrair_edgv_com_versao_oficial(arquivo_xml, ns)

    except Exception as e:
        print(f"Erro ao extrair metadados do XML: {e}")

    return escala, data_do_produto, esquema, metadata_id

def abrir_datasource(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    caminho_gdal = caminho.replace("\\", "/")
    if ext == ".zip":
        caminho_gdal = f"/vsizip/{caminho_gdal}"
        ds = ogr.Open(caminho_gdal)
    elif ext in [".gpkg", ".gpkx"]:
        ds = ogr.Open(caminho_gdal)
    else:
        ds = None
    return ds

def open_destination_datasource(conn_str):
    #conn_str = "PG: host=localhost dbname=your_db user=your_user password=your_password"

    # Open the PostGIS data source
    ds = ogr.Open(conn_str, update=1)  # update=1 means it's writable
    if ds is None:
        raise RuntimeError("Could not open PostGIS database.")

    return ds


def remove_all_geometries_with_metadataid(ds, table_name, metadata_id):
    layer = ds.ExecuteSQL(f"""
        SELECT 1 FROM {table_name} where metadata_id = '{metadata_id}' limit 1
        """)
    feature_count = layer.GetFeatureCount()
    if feature_count>0:
        layer = ds.ExecuteSQL(f"""
        DELETE FROM {table_name} where metadata_id = '{metadata_id}'
        """)
    return 

def check_product_exists(ds, table_name, metadata_id):
    layer = ds.ExecuteSQL(
        f"""
        SELECT 1 FROM {table_name} where metadata_id = '{metadata_id}' limit 1
        """)
     
    return layer.GetFeatureCount()>0

def importar_para_tabela(file_path, table_name, xml=None):
    if file_path.lower().endswith(".xml"):
        safe_print(f"📄 Arquivo XML detectado (não vetorial): {file_path} - ignorado.")
        return

    safe_print(f"\n📦 Importando: {os.path.basename(file_path)}")

    escala, data_do_produto, esquema, metadata_id = extract_metadata_from_xml(xml)
    if not metadata_id:
        metadata_id = os.path.basename(file_path)

    datasource = abrir_datasource(file_path)
    if datasource is None or datasource.GetLayerCount() == 0:
        safe_print(f"⚠️ Ignorando arquivo (não vetor ou sem camadas): {file_path}")
        return

    conn = "PG: "+' '.join(f'{k}={v}' for k, v in CONFIG_BANCO.items())

    print(conn)
    out_datasource = open_destination_datasource(conn)
    count = 0

    if check_product_exists(out_datasource, table_name, metadata_id): #posteriormente, isso deve remover o atual
        safe_print("Removendo dados existentes.")
        remove_all_geometries_with_metadataid(out_datasource, table_name, metadata_id)

    out_layer = out_datasource.GetLayerByName(table_name)

    for layer in datasource:
        nome_classe = layer.GetName()
        for feature in layer:
            geom = feature.GetGeometryRef()
            if not geom:
                continue
            
            geom_type = geom.GetGeometryType()

            if geom_type == ogr.wkbPoint or geom_type == ogr.wkbPoint25D:
                geom = ogr.ForceToMultiPoint(geom)
            elif geom_type == ogr.wkbLineString or geom_type == ogr.wkbLineString25D:
                geom = ogr.ForceToMultiLineString(geom)
            elif geom_type == ogr.wkbPolygon or geom_type == ogr.wkbPolygon25D:
                geom = ogr.ForceToMultiPolygon(geom)


            #wkt = geom.ExportToWkt()
            feature_json = json.loads(feature.ExportToJson())
            atributos_dict = feature_json.get("properties", {})
            atributos_corrigidos = {
                k: (str(v).encode("utf-8", errors="replace").decode("utf-8", errors="replace") if v is not None else None)
                for k, v in atributos_dict.items()
            }
            atributos = json.dumps(atributos_corrigidos, ensure_ascii=False ) #

            feature_defn = out_layer.GetLayerDefn()
            feature = ogr.Feature(feature_defn)

            # Set attribute values
            feature.SetField("json", atributos)
            feature.SetField("classe", nome_classe)
            feature.SetField("metadata_id", metadata_id)
            feature.SetField("escala", escala)
            feature.SetField("data_do_produto", data_do_produto)
            feature.SetField("esquema", esquema)
            feature.SetGeometry(geom)

            # Insert the feature into the layer
            out_layer.CreateFeature(feature)
            
            '''cur.execute(
                f"""
                INSERT INTO {table_name} 
                (geometria, json, classe, metadata_id, escala, data_do_produto, esquema)
                VALUES 
                (ST_GeomFromText(%s, 4326), %s, %s, %s, %s, %s, %s);
                """,
                (wkt, atributos, nome_classe, metadata_id, escala, data_do_produto, esquema),
            )'''
            count += 1
    out_datasource = None
    safe_print(f"✅ {count} feições importadas de '{os.path.basename(file_path)}'.")

def find_xml_for_file(caminho_arquivo):
    base = os.path.splitext(caminho_arquivo)[0]
    caminho_xml = base + ".xml"
    return caminho_xml if os.path.exists(caminho_xml) else None

if __name__ == "__main__":
    importar_todos = []
    for root, dirs, files in os.walk(PASTA_ARQUIVOS):
        for file in files:
            ext = file.lower().split('.')[-1]
            if ext in ["zip", "gpkg"]:
                caminho_completo = os.path.join(root, file)
                importar_todos.append(caminho_completo)

    for caminho in importar_todos:
        xml_associado = find_xml_for_file(caminho)
        try:
            importar_para_tabela(caminho, TABELA_GLOBAL, xml_associado)
        except Exception as e:
            safe_print(f"❌ Erro ao processar '{caminho}': {e}")

    safe_print("🚀 Processo finalizado.")
