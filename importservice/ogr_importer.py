import os
import re
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
TABELA_GEOMETRIAS = "importacao_geometrias"
PASTA_ARQUIVOS = os.getenv("PASTA_ARQUIVOS")

def _pick_edgv_version(text: str):
    """Retorna '2.1.3' ou '3.0' se aparecer no texto."""
    if not text:
        return None
    m = re.search(r'(2[\._-]?1[\._-]?3|3\.0)', text, flags=re.IGNORECASE)
    return m.group(1).replace('_','.') if m else None

def _parse_xml_from_locator(xml_locator):
    """Abre o XML a partir do localizador retornado por find_xml_for_file."""
    if not xml_locator:
        return None
    kind = xml_locator[0]
    if kind == "fs":
        return ET.parse(xml_locator[1])
    if kind == "zip":
        zip_path, member = xml_locator[1], xml_locator[2]
        with zipfile.ZipFile(zip_path, "r") as zf:
            with zf.open(member) as fh:
                return ET.parse(fh)
    return None

def extrair_edgv_com_versao_oficial_from_tree(tree):
    """Retorna 'EDGV 2.1.3' / 'EDGV 3.0' se achar; senão 'EDGV'."""
    try:
        root = tree.getroot()
        ns = {
            'gmd': "http://www.isotc211.org/2005/gmd",
            'gco': "http://www.isotc211.org/2005/gco",
            'gmx': "http://www.isotc211.org/2005/gmx",
        }
        xpaths = [
            './/gmd:contentInfo//gmd:MD_FeatureCatalogueDescription//gmd:featureCatalogueCitation//gmd:CI_Citation/gmd:edition/gco:CharacterString',
            './/gmd:contentInfo//gmd:MD_FeatureCatalogueDescription//gmd:featureCatalogueCitation//gmd:CI_Citation/gmd:title/gco:CharacterString',
            './/gmd:featureCatalogueCitation//gmd:CI_Citation/gmd:edition/gco:CharacterString',
            './/gmd:featureCatalogueCitation//gmd:CI_Citation/gmd:title/gco:CharacterString',
            './/gmd:identificationInfo//gmd:citation//gmd:CI_Citation/gmd:edition/gco:CharacterString',
            './/gmd:identificationInfo//gmd:citation//gmd:CI_Citation/gmd:title/gco:CharacterString',
            './/gmx:FC_FeatureCatalogue/gmx:versionNumber/gco:CharacterString',
            './/gmx:FC_FeatureCatalogue/gmx:name/gco:CharacterString',
            './/gmd:identificationInfo//gmd:abstract/gco:CharacterString',
            './/gmd:descriptiveKeywords//gco:CharacterString',
        ]
        for xp in xpaths:
            for el in root.findall(xp, ns):
                ver = _pick_edgv_version(el.text)
                if ver:
                    return f"EDGV {ver.replace('-', '.')}"

        # Fallback varrendo tudo
        for xp in ['.//gco:CharacterString',
                   './/gmd:PT_FreeText//gmd:LocalisedCharacterString',
                   './/gmx:Anchor']:
            for el in root.findall(xp, ns):
                ver = _pick_edgv_version(el.text)
                if ver:
                    return f"EDGV {ver.replace('-', '.')}"
    except Exception as e:
        safe_print(f"❌ Erro extraindo versão EDGV: {e}")
    return "EDGV"

def criar_banco_postgis(nome_banco):
    try:
        conn = psycopg2.connect(
            dbname='postgres',
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

def safe_print(msg):
    print(msg, flush=True)

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

def extract_metadata_from_xml(xml_locator):
    escala = "Não informada"
    data_do_produto = None
    esquema = "EDGV"
    metadata_id = "Não informado"

    tree = _parse_xml_from_locator(xml_locator)
    if tree is None:
        safe_print("⚠️ XML não encontrado/legível; usando defaults.")
        return escala, data_do_produto, esquema, metadata_id

    try:
        ns = {'gmd': "http://www.isotc211.org/2005/gmd", 'gco': "http://www.isotc211.org/2005/gco"}

        esc = tree.find('.//gmd:equivalentScale//gco:Integer', ns)
        if esc is not None and esc.text:
            escala = f"1:{esc.text.strip()}"
            safe_print(f"📊 Escala encontrada: {escala}")

        dt = tree.find('.//gmd:CI_Date/gmd:date/gco:Date', ns)
        if dt is not None and dt.text:
            data_do_produto = dt.text.strip()
            safe_print(f"📅 Data encontrada: {data_do_produto}")

        fid = tree.find('.//gmd:fileIdentifier//gco:CharacterString', ns)
        if fid is not None and fid.text:
            metadata_id = fid.text.strip()
            safe_print(f"🆔 Metadata ID encontrado: {metadata_id}")

        esquema = extrair_edgv_com_versao_oficial_from_tree(tree)  # => 'EDGV 2.1.3' / 'EDGV 3.0' / 'EDGV'
        safe_print(f"📋 Esquema (XML): {esquema}")

    except Exception as e:
        safe_print(f"❌ Erro ao extrair metadados do XML: {e}")

    safe_print(f"📦 Metadados -> Escala: {escala}, Data: {data_do_produto}, Esquema: {esquema}, Metadata ID: {metadata_id}")
    return escala, data_do_produto, esquema, metadata_id

def abrir_datasources(caminho):
    ext = os.path.splitext(caminho)[1].lower()
    vsi = os.path.abspath(caminho).replace("\\", "/")
    
    if ext == ".zip":
        root = f"/vsizip/{vsi}"
        datas = []

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

def check_product_exists(ds, table_name, metadata_id):
    layer = ds.ExecuteSQL(
        f"SELECT 1 FROM {table_name} WHERE metadata_id = '{metadata_id}' LIMIT 1"
    )
    return layer.GetFeatureCount() > 0 if layer else False

def remove_all_geometries_with_metadataid(ds, table_name, metadata_id):
    ds.ExecuteSQL(f"DELETE FROM {table_name} WHERE metadata_id = '{metadata_id}'")

def _canon_esquema_label(texto: str, file_path: str = "") -> str:
    """Retorna 'EDGV 3.0', 'EDGV 2.1.3' ou 'EDGV' a partir do XML ou do nome do arquivo/pasta."""
    t = (texto or "").lower()
    p = (file_path or "").lower()

    def has_213(s):  # aceita 2.1.3 / 2_1_3 / 2-1-3 / 213
        return bool(re.search(r'2[\._-]?1[\._-]?3', s))

    if "3.0" in t or "3.0" in p:
        return "EDGV 3.0"
    if has_213(t) or has_213(p):
        return "EDGV 2.1.3"
    return "EDGV"

def importar_para_tabela(file_path, table_name, xml_locator=None):
    safe_print(f"\n📦 Importando: {os.path.basename(file_path)}")

    escala, data_do_produto, esquema, metadata_id = extract_metadata_from_xml(xml_locator)
    esquema = _canon_esquema_label(esquema, file_path)

    if metadata_id == "Não informado":
        metadata_id = os.path.basename(file_path)
        safe_print(f"🆔 Usando nome do arquivo como Metadata ID: {metadata_id}")

    datasources = abrir_datasources(file_path)
    if not datasources:
        safe_print(f"⚠️ Ignorando '{file_path}': sem vetores suportados.")
        return

    conn_str = "PG: " + " ".join(f"{k}={v}" for k, v in CONFIG_BANCO.items())
    ds_out = ogr.Open(conn_str, update=1)
    if not ds_out:
        raise RuntimeError("❌ Falha na conexão com banco de dados.")
    layer_out = ds_out.GetLayerByName(table_name)

    if check_product_exists(ds_out, table_name, metadata_id):
        safe_print("🔁 Removendo feições antigas…")
        remove_all_geometries_with_metadataid(ds_out, table_name, metadata_id)

    count = 0
    target_srs = osr.SpatialReference(); target_srs.ImportFromEPSG(3857)

    for ds in datasources:
        for layer in ds:
            nome_classe = layer.GetName()
            safe_print(f"🎯 Processando camada: '{nome_classe}'")

            source_srs = layer.GetSpatialRef()
            transform = None
            if source_srs and not source_srs.IsSame(target_srs):
                transform = osr.CoordinateTransformation(source_srs, target_srs)
            elif not source_srs:
                safe_print(f"⚠️ Camada '{nome_classe}' sem SRS; mantendo geometria.")

            for feat in layer:
                geom = feat.GetGeometryRef()
                if not geom:
                    continue

                if transform:
                    geom = geom.Clone()
                    geom.Transform(transform)

                gt = geom.GetGeometryType()
                if gt in (ogr.wkbPoint, ogr.wkbPoint25D):
                    geom = ogr.ForceToMultiPoint(geom)
                elif gt in (ogr.wkbLineString, ogr.wkbLineString25D):
                    geom = ogr.ForceToMultiLineString(geom)
                elif gt in (ogr.wkbPolygon, ogr.wkbPolygon25D):
                    geom = ogr.ForceToMultiPolygon(geom)

                props = json.loads(feat.ExportToJson())["properties"]
                clean = {k: (str(v).encode("utf-8", errors="replace").decode("utf-8", errors="replace") if v is not None else None)
                         for k, v in props.items()}
                json_attr = json.dumps(clean, ensure_ascii=False)

                fo = ogr.Feature(layer_out.GetLayerDefn())
                fo.SetField("json", json_attr)
                fo.SetField("classe", nome_classe)
                fo.SetField("metadata_id", metadata_id)
                fo.SetField("escala", escala)
                fo.SetField("data_do_produto", data_do_produto)
                fo.SetField("esquema", esquema)  # <-- 'EDGV 2.1.3' / 'EDGV 3.0' / 'EDGV'
                fo.SetGeometry(geom)
                layer_out.CreateFeature(fo)
                count += 1
        ds = None

    ds_out = None
    safe_print(f"✅ {count} feições importadas de '{os.path.basename(file_path)}'.")

def find_xml_for_file(caminho_arquivo):
    """
    Retorna:
      - ('fs', '/abs/caminho/arquivo.xml') se o XML estiver no sistema de arquivos
      - ('zip', '/abs/caminho/pacote.zip', 'nome/inside.xml') se estiver dentro do .zip
      - None se não encontrar
    """
    ext = os.path.splitext(caminho_arquivo)[1].lower()

    # Se o próprio caminho já é um XML
    if ext == ".xml" and os.path.exists(caminho_arquivo):
        safe_print(f"📄 XML encontrado (fs): {caminho_arquivo}")
        return ("fs", caminho_arquivo)

    # Se for zip, procurar um XML lá dentro
    if ext == ".zip" and os.path.exists(caminho_arquivo):
        try:
            with zipfile.ZipFile(caminho_arquivo, "r") as zf:
                xmls = [n for n in zf.namelist() if n.lower().endswith(".xml")]
                if xmls:
                    # prioriza nomes típicos
                    def score(n):
                        nlow = n.lower()
                        return (
                            0 if re.search(r'metad|metadata|metadado|ident|edgv|catalog|feature', nlow) else 1,
                            len(n)
                        )
                    xmls.sort(key=score)
                    safe_print(f"📄 XML encontrado (zip): {xmls[0]}")
                    return ("zip", caminho_arquivo, xmls[0])
        except Exception as e:
            safe_print(f"❌ Erro analisando ZIP: {e}")

    # Um XML com mesmo nome-base ao lado
    base = os.path.splitext(caminho_arquivo)[0]
    xml_lateral = base + ".xml"
    if os.path.exists(xml_lateral):
        safe_print(f"📄 XML encontrado (lateral): {xml_lateral}")
        return ("fs", xml_lateral)

    safe_print(f"⚠️ XML não encontrado para: {caminho_arquivo}")
    return None

def aplicar_mapeamento_via_sql(table_name):
    try:
        conn = psycopg2.connect(**CONFIG_BANCO)
        cur = conn.cursor()

        # Índices para acelerar o join
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{table_name}_classe_esquema ON {table_name} (classe, esquema);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_importservice_rep_classe_esquema ON importservice_representacaografica (classe, esquema);")

        # 1) Join por classe+esquema (ambos normalizados em lower)
        cur.execute(f"""
            WITH rep AS (
              SELECT lower(trim(classe))   AS classe_norm,
                     lower(trim(esquema))  AS esquema_norm,
                     trim(coalesce(grupo_representacao,'OUTRO')) AS grupo
              FROM importservice_representacaografica
            )
            UPDATE {table_name} g
            SET graphic_representation_group = r.grupo
            FROM rep r
            WHERE lower(g.classe)  = r.classe_norm
              AND lower(g.esquema) = r.esquema_norm;
        """)

        # 2) Fallback: onde não casou, usar só a classe (independente de esquema)
        cur.execute(f"""
            UPDATE {table_name} g
            SET graphic_representation_group = r.grupo
            FROM (
              SELECT lower(trim(classe)) AS classe_norm,
                     min(trim(coalesce(grupo_representacao,'OUTRO'))) AS grupo
              FROM importservice_representacaografica
              GROUP BY 1
            ) r
            WHERE (g.graphic_representation_group IS NULL OR g.graphic_representation_group = '' OR g.graphic_representation_group = 'OUTRO')
              AND lower(g.classe) = r.classe_norm;
        """)

        # 3) Garante valor
        cur.execute(f"""
            UPDATE {table_name}
            SET graphic_representation_group = 'OUTRO'
            WHERE graphic_representation_group IS NULL OR graphic_representation_group = '';
        """)

        conn.commit()
        cur.close(); conn.close()
        safe_print("✅ Esquema gravado como 'EDGV X.Y.Z' e grupos atualizados via SQL.")
    except Exception as e:
        print(f"❌ Erro ao atualizar grupos via SQL: {e}")

# Execução principal
if __name__ == "__main__":
    nome_banco = CONFIG_BANCO["dbname"]
        
    # Cria banco se não existir
    criar_banco_postgis(nome_banco)
    # Ativa PostGIS no banco
    ativar_postgis(nome_banco)
    # Monta string de conexão GDAL
    conn_str = "PG: " + ' '.join(f"{k}={v}" for k, v in CONFIG_BANCO.items())
    verificar_ou_criar_tabela(TABELA_GEOMETRIAS, conn_str)

    importar_todos = []
    for root, dirs, files in os.walk(PASTA_ARQUIVOS):
        for file in files:
            if file.lower().endswith(("zip", "gpkg")):
                importar_todos.append(os.path.join(root, file))

    for caminho in importar_todos:
        xml_associado = find_xml_for_file(caminho)
        try:
            importar_para_tabela(caminho, TABELA_GEOMETRIAS, xml_associado)
        except Exception as e:
            safe_print(f"❌ Erro ao processar '{caminho}': {e}")

    # Atualiza os grupos com base no Django Admin:
    aplicar_mapeamento_via_sql(TABELA_GEOMETRIAS)

    safe_print("🚀 Processo finalizado.")