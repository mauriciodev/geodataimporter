import os
import json
import zipfile
import xml.etree.ElementTree as ET
from osgeo import ogr, osr
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))
ogr.UseExceptions()

# Configurações do banco
CONFIG_BASE = {
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}
CONFIG_BANCO = {**CONFIG_BASE, "dbname": os.getenv("DB_NAME")}
TABELA_GLOBAL = "importacao_geometrias"
PASTA_ARQUIVOS = os.getenv("PASTA_ARQUIVOS")



def criar_banco_postgis(nome_banco):
    try:
        conn = psycopg2.connect(
            dbname='postgres',  # conecta no banco padrão para criar o seu
            user=CONFIG_BASE['user'],
            password=CONFIG_BASE['password'],
            host=CONFIG_BASE['host'],
            port=CONFIG_BASE['port']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (nome_banco,))
        if cursor.fetchone():
            print(f"🗃️ Banco '{nome_banco}' já existe.")
        else:
            cursor.execute(f'CREATE DATABASE "{nome_banco}";')
            print(f"✅ Banco '{nome_banco}' criado com sucesso.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao criar banco: {e}")

def ativar_postgis(nome_banco):
    try:
        conn = psycopg2.connect(
            dbname=nome_banco,
            user=CONFIG_BASE['user'],
            password=CONFIG_BASE['password'],
            host=CONFIG_BASE['host'],
            port=CONFIG_BASE['port']
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
        print(f"🧩 Extensão PostGIS ativada no banco '{nome_banco}'.")

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Erro ao ativar PostGIS: {e}")

# Impressão segura no console
def safe_print(msg):
    print(msg, flush=True)

# Criação da tabela caso não exista
def verificar_ou_criar_tabela(table_name, conn_str, srid=3857):
    ds = ogr.Open(conn_str, update=1)
    if ds is None:
        raise RuntimeError("❌ Não foi possível conectar ao banco.")

    if ds.GetLayerByName(table_name):
        print(f"🧾 Tabela '{table_name}' já existe.")
    else:
        print(f"📐 Criando tabela '{table_name}'...")

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(srid)

        layer = ds.CreateLayer(
            table_name, srs,
            geom_type=ogr.wkbUnknown,
            options=['GEOMETRY_NAME=wkb_geometry', 'DIM=2']
        )
        if layer is None:
            raise RuntimeError("❌ Falha ao criar a camada.")

        campos = [
            ("json", ogr.OFTString),     
            ("classe", ogr.OFTString),
            ("metadata_id", ogr.OFTString),
            ("escala", ogr.OFTString),
            ("data_do_produto", ogr.OFTDate),
            ("esquema", ogr.OFTString),
            ("graphic_representation_group", ogr.OFTString)
        ]

        for nome, tipo in campos:
            campo = ogr.FieldDefn(nome, tipo)
            campo.SetWidth(2048)
            layer.CreateField(campo)

        print(f"✅ Tabela '{table_name}' criada com sucesso.")

    ds = None
    try:
        conn_pg = psycopg2.connect(**CONFIG_BANCO)
        cur = conn_pg.cursor()
        cur.execute(f"""
            ALTER TABLE {table_name}
            ALTER COLUMN json TYPE JSONB
            USING json::jsonb;
        """)
        conn_pg.commit()
        cur.close()
        conn_pg.close()
        print("🧬 Campo 'json' convertido para JSONB com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao converter campo para JSONB: {e}")

    criar_indices_pos_importacao(table_name)

def criar_indices_pos_importacao(table_name):
    try:
        conn = psycopg2.connect(**CONFIG_BANCO)
        cursor = conn.cursor()

        # Índice para a coluna "classe"
        cursor.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes WHERE tablename = %s AND indexname = %s
                ) THEN
                    EXECUTE 'CREATE INDEX idx_{table_name}_classe ON {table_name} (classe)';
                END IF;
            END$$;
        """, (table_name, f"idx_{table_name}_classe"))

        conn.commit()
        cursor.close()
        conn.close()
        safe_print(f"✅ Índice da coluna 'classe' criado na tabela {table_name}.")

    except Exception as e:
        print(f"❌ Erro ao criar índices na tabela {table_name}: {e}")

'''def registrar_geometry_column_postgis(table_name, column_name="wkb_geometry", srid=3857, geom_type="GEOMETRY", dim=2):
    try:
        conn = psycopg2.connect(**CONFIG_BANCO)
        cursor = conn.cursor()

        cursor.execute(f"""
            SELECT 1 FROM geometry_columns
            WHERE f_table_name = %s AND f_geometry_column = %s
        """, (table_name, column_name))
        exists = cursor.fetchone()

        if not exists:
            cursor.execute(f"""
                SELECT AddGeometryColumn(
                    'public', %s, %s, %s, %s, %s
                );
            """, (table_name, column_name, srid, geom_type, dim))
            safe_print(f"📌 AddGeometryColumn executado com sucesso em '{table_name}.{column_name}'.")
        else:
            safe_print(f"ℹ️ AddGeometryColumn pulado: entrada já existe para '{table_name}.{column_name}'.")

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        safe_print(f"❌ Erro ao executar AddGeometryColumn: {e}")
'''
# Extração de metadados do XML
def extrair_edgv_com_versao_oficial(xml_path, namespaces):
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        citations = root.findall('.//gmd:featureCatalogueCitation/gmd:CI_Citation', namespaces)
        for cit in citations:
            title = cit.find('gmd:title/gco:CharacterString', namespaces)
            edition = cit.find('gmd:edition/gco:CharacterString', namespaces)

            if title is not None and edition is not None:
                return f"{title.text.strip()} {edition.text.strip()}"
        return "EDGV"
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
def abrir_datasources(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    vsi = os.path.abspath(caminho).replace("\\", "/")
    
    if ext == ".zip":
        root = f"/vsizip/{vsi}"
        datas = []

        # log e extração dos shapefiles dentro do ZIP
        with zipfile.ZipFile(caminho, "r") as zf:
            safe_print("📁 Conteúdo do ZIP:")
            for name in zf.namelist():
                safe_print(f" - {name}")

            shp_files = [n for n in zf.namelist() if n.lower().endswith(".shp")]

        if not shp_files:
            safe_print("⚠️ Nenhum arquivo .shp encontrado dentro do ZIP.")
            return []

        for shp in shp_files:
            uri = f"/vsizip/{vsi}/{shp}"
            try:
                ds_shp = ogr.Open(uri)
                if ds_shp and ds_shp.GetLayerCount() > 0:
                    datas.append(ds_shp)
                    safe_print(f"✅ Shapefile carregado: {shp}")
                else:
                    safe_print(f"⚠️ Ignorado: '{shp}' não contém camadas válidas.")
            except Exception as e:
                safe_print(f"❌ Erro ao abrir '{shp}': {e}")

        return datas

    else:
        ds = ogr.Open(vsi)
        return [ds] if ds and ds.GetLayerCount() > 0 else []

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
def importar_para_tabela(file_path, table_name, xml=None, ET_EDGV_GROUPS={}):
    safe_print(f"\n📦 Importando: {os.path.basename(file_path)}")

    # metadados
    escala, data_do_produto, esquema, metadata_id = extract_metadata_from_xml(xml)
    if not metadata_id:
        metadata_id = os.path.basename(file_path)

    # abre TODOS os datasources
    datasources = abrir_datasources(file_path)
    if not datasources:
        safe_print(f"⚠️ Ignorando '{file_path}': sem vetores suportados.")
        return

    # abre OGR/PostGIS de saída
    conn_str = "PG: " + " ".join(f"{k}={v}" for k,v in CONFIG_BANCO.items())
    ds_out = ogr.Open(conn_str, update=1)
    if not ds_out:
        raise RuntimeError("❌ Falha na conexão com banco de dados.")
    layer_out = ds_out.GetLayerByName(table_name)

    # remove antigos
    if check_product_exists(ds_out, table_name, metadata_id):
        safe_print("🔁 Removendo feições antigas…")
        remove_all_geometries_with_metadataid(ds_out, table_name, metadata_id)

    count = 0
    # percorre cada DataSource e cada camada
    for ds in datasources:
        for layer in ds:
            nome_classe = layer.GetName()
            for feat in layer:
                geom = feat.GetGeometryRef()
                if not geom:
                    continue

                # Reprojetar para EPSG:3857
                source_srs = layer.GetSpatialRef()
                target_srs = osr.SpatialReference()
                target_srs.ImportFromEPSG(3857)
                transform = osr.CoordinateTransformation(source_srs, target_srs)
                geom.Transform(transform)

                # normaliza multipartes
                gt = geom.GetGeometryType()
                if gt in (ogr.wkbPoint, ogr.wkbPoint25D):
                    geom = ogr.ForceToMultiPoint(geom)
                elif gt in (ogr.wkbLineString, ogr.wkbLineString25D):
                    geom = ogr.ForceToMultiLineString(geom)
                elif gt in (ogr.wkbPolygon, ogr.wkbPolygon25D):
                    geom = ogr.ForceToMultiPolygon(geom)

                props = json.loads(feat.ExportToJson())["properties"]
                clean = {
                    k: str(v).encode("utf-8", errors="replace")
                          .decode("utf-8", errors="replace")
                    if v is not None else None
                    for k,v in props.items()
                }
                json_attr = json.dumps(clean, ensure_ascii=False)

                fo = ogr.Feature(layer_out.GetLayerDefn())
                fo.SetField("json", json_attr)
                fo.SetField("classe", nome_classe)
                fo.SetField("metadata_id", metadata_id)
                fo.SetField("escala", escala)
                fo.SetField("data_do_produto", data_do_produto)
                fo.SetField("esquema", esquema)
                graphic_group = ET_EDGV_GROUPS.get(nome_classe, "OUTRO")  # "OUTRO" se não houver mapeamento
                fo.SetField("graphic_representation_group", graphic_group)
                fo.SetGeometry(geom)
                layer_out.CreateFeature(fo)
                count += 1

        # fecha DataSource auxiliar
        ds = None

    # fecha saída
    ds_out = None
    safe_print(f"✅ {count} feições importadas de '{os.path.basename(file_path)}'.")

# Busca XML correspondente
def find_xml_for_file(caminho_arquivo):
    base = os.path.splitext(caminho_arquivo)[0]
    caminho_xml = base + ".xml"
    return caminho_xml if os.path.exists(caminho_xml) else None



# Execução principal
if __name__ == "__main__":
    nome_banco = CONFIG_BANCO["dbname"]
    # Cria banco se não existir
    criar_banco_postgis(nome_banco)
    # Ativa PostGIS no banco
    ativar_postgis(nome_banco)
    # Monta string de conexão GDAL
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

