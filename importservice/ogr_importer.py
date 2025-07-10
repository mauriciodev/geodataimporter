import os
import json
import xml.etree.ElementTree as ET
from osgeo import ogr, osr

ogr.UseExceptions()

# Configurações do banco
CONFIG_BASE = {
    "user": "postgres",
    "password": "postgres",
    "host": "localhost",
    "port": "5433",
}
CONFIG_BANCO = {**CONFIG_BASE, "dbname": "pfc2025"}
TABELA_GLOBAL = "importacao_geometrias"
PASTA_ARQUIVOS = r"C:\\Users\\gabri\\OneDrive\\Área de Trabalho\\Estudos\\Eng Cartografica\\5.1\\PFC\\arquivos"

# Impressão segura no console
def safe_print(msg):
    print(msg, flush=True)

# Criação da tabela caso não exista
def verificar_ou_criar_tabela(table_name, conn_str, srid=4326):
    ds = ogr.Open(conn_str, update=1)
    if ds is None:
        raise RuntimeError("❌ Não foi possível conectar ao banco.")

    if ds.GetLayerByName(table_name):
        print(f"🧾 Tabela '{table_name}' já existe.")
        return

    print(f"📐 Criando tabela '{table_name}'...")

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(srid)

    layer = ds.CreateLayer(table_name, srs, geom_type=ogr.wkbUnknown)
    if layer is None:
        raise RuntimeError("❌ Falha ao criar a camada.")

    campos = [
        ("json", ogr.OFTString),
        ("classe", ogr.OFTString),
        ("metadata_id", ogr.OFTString),
        ("escala", ogr.OFTString),
        ("data_do_produto", ogr.OFTString),
        ("esquema", ogr.OFTString)
    ]

    for nome, tipo in campos:
        campo = ogr.FieldDefn(nome, tipo)
        campo.SetWidth(512)
        layer.CreateField(campo)

    print(f"✅ Tabela '{table_name}' criada com sucesso.")

# Extração de metadados do XML
def extrair_edgv_com_versao_oficial(xml_path, namespaces):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        title = root.find('.//gmd:title/gco:CharacterString', namespaces)
        edition = root.find('.//gmd:edition/gco:CharacterString', namespaces)
        edition_date = root.find('.//gmd:editionDate/gco:Date', namespaces)
        return f"{title.text} {edition.text} {edition_date.text}" if title is not None else "EDGV"
    except Exception as e:
        print(f"Erro ao processar XML (extrair_edgv): {e}")
        return None

def extract_metadata_from_xml(arquivo_xml):
    escala = data_do_produto = esquema = metadata_id = None
    if not arquivo_xml or not os.path.exists(arquivo_xml):
        return escala, data_do_produto, esquema, metadata_id
    try:
        tree = ET.parse(arquivo_xml)
        ns = {
            'gmd': "http://www.isotc211.org/2005/gmd",
            'gco': "http://www.isotc211.org/2005/gco"
        }

        escala_elem = tree.find('.//gmd:equivalentScale//gco:Integer', ns)
        if escala_elem is not None:
            escala = f"1:{escala_elem.text.strip()}"

        data_elem = tree.find('.//gmd:CI_Date/gmd:date/gco:Date', ns)
        if data_elem is not None:
            data_do_produto = data_elem.text.strip()

        file_id_elem = tree.find('.//gmd:fileIdentifier//gco:CharacterString', ns)
        if file_id_elem is not None:
            metadata_id = file_id_elem.text.strip()

        esquema = extrair_edgv_com_versao_oficial(arquivo_xml, ns)

    except Exception as e:
        print(f"Erro ao extrair metadados do XML: {e}")

    return escala, data_do_produto, esquema, metadata_id

# Abre GPKG ou ZIP
def abrir_datasource(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    caminho_gdal = caminho.replace("\\", "/")
    if ext == ".zip":
        caminho_gdal = f"/vsizip/{caminho_gdal}"
    return ogr.Open(caminho_gdal)

# Verifica se produto já existe na tabela
def check_product_exists(ds, table_name, metadata_id):
    layer = ds.ExecuteSQL(
        f"SELECT 1 FROM {table_name} WHERE metadata_id = '{metadata_id}' LIMIT 1"
    )
    return layer.GetFeatureCount() > 0 if layer else False

# Remove registros com mesmo metadata_id
def remove_all_geometries_with_metadataid(ds, table_name, metadata_id):
    ds.ExecuteSQL(f"DELETE FROM {table_name} WHERE metadata_id = '{metadata_id}'")

# Importa o arquivo
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
        safe_print(f"⚠️ Ignorando arquivo (sem vetores): {file_path}")
        return

    conn_str = "PG: " + ' '.join(f"{k}={v}" for k, v in CONFIG_BANCO.items())
    ds_out = ogr.Open(conn_str, update=1)
    if ds_out is None:
        raise RuntimeError("❌ Falha na conexão com banco de dados.")

    if check_product_exists(ds_out, table_name, metadata_id):
        safe_print("🔁 Dados existentes encontrados. Removendo para substituir.")
        remove_all_geometries_with_metadataid(ds_out, table_name, metadata_id)

    layer_out = ds_out.GetLayerByName(table_name)
    count = 0

    for layer in datasource:
        nome_classe = layer.GetName()
        for feature in layer:
            geom = feature.GetGeometryRef()
            if not geom:
                continue

            # Converter para tipos multiparte
            geom_type = geom.GetGeometryType()
            if geom_type in [ogr.wkbPoint, ogr.wkbPoint25D]:
                geom = ogr.ForceToMultiPoint(geom)
            elif geom_type in [ogr.wkbLineString, ogr.wkbLineString25D]:
                geom = ogr.ForceToMultiLineString(geom)
            elif geom_type in [ogr.wkbPolygon, ogr.wkbPolygon25D]:
                geom = ogr.ForceToMultiPolygon(geom)

            props = json.loads(feature.ExportToJson()).get("properties", {})
            props_corrigidos = {
                k: str(v).encode("utf-8", errors="replace").decode("utf-8", errors="replace")
                if v is not None else None for k, v in props.items()
            }
            json_atributos = json.dumps(props_corrigidos, ensure_ascii=False)

            feat_out = ogr.Feature(layer_out.GetLayerDefn())
            feat_out.SetField("json", json_atributos)
            feat_out.SetField("classe", nome_classe)
            feat_out.SetField("metadata_id", metadata_id)
            feat_out.SetField("escala", escala)
            feat_out.SetField("data_do_produto", data_do_produto)
            feat_out.SetField("esquema", esquema)
            feat_out.SetGeometry(geom)
            layer_out.CreateFeature(feat_out)

            count += 1

    ds_out = None
    safe_print(f"✅ {count} feições importadas de '{os.path.basename(file_path)}'.")

# Busca XML correspondente
def find_xml_for_file(caminho_arquivo):
    base = os.path.splitext(caminho_arquivo)[0]
    caminho_xml = base + ".xml"
    return caminho_xml if os.path.exists(caminho_xml) else None

# Execução principal
if __name__ == "__main__":
    conn_str = "PG: " + ' '.join(f"{k}={v}" for k, v in CONFIG_BANCO.items())
    verificar_ou_criar_tabela(TABELA_GLOBAL, conn_str)

    importar_todos = []
    for root, dirs, files in os.walk(PASTA_ARQUIVOS):
        for file in files:
            if file.lower().endswith(("zip", "gpkg")):
                importar_todos.append(os.path.join(root, file))

    for caminho in importar_todos:
        xml_associado = find_xml_for_file(caminho)
        try:
            importar_para_tabela(caminho, TABELA_GLOBAL, xml_associado)
        except Exception as e:
            safe_print(f"❌ Erro ao processar '{caminho}': {e}")

    safe_print("🚀 Processo finalizado.")
