from osgeo import ogr

def criar_tabela_postgis(nome_tabela, tipo_geometria, nome_banco, usuario, senha, host='localhost', porta=5432, srid=4326):
    # Mapeamento de tipo de geometria como string -> OGR type
    tipo_ogr = {
        'POINT': ogr.wkbPoint,
        'LINESTRING': ogr.wkbLineString,
        'POLYGON': ogr.wkbPolygon,
        'MULTIPOINT': ogr.wkbMultiPoint,
        'MULTILINESTRING': ogr.wkbMultiLineString,
        'MULTIPOLYGON': ogr.wkbMultiPolygon
    }

    tipo_geom = tipo_geometria.upper()
    if tipo_geom not in tipo_ogr:
        raise ValueError(f"Tipo de geometria '{tipo_geom}' não suportado.")

    # String de conexão OGR para PostGIS
    conn_str = (
        f"PG: host='{host}' port='{porta}' dbname='{nome_banco}' user='{usuario}' password='{senha}'"
    )

    # Abrir conexão com o banco
    ds = ogr.Open(conn_str, update=1)  # update=1 para permitir escrita
    if ds is None:
        raise ConnectionError("Não foi possível conectar ao banco de dados.")

    # Criar Spatial Reference
    srs = ogr.osr.SpatialReference()
    srs.ImportFromEPSG(srid)

    # Criar a camada (layer)
    layer = ds.CreateLayer(nome_tabela, srs, tipo_ogr[tipo_geom])
    if layer is None:
        raise RuntimeError("Não foi possível criar a camada (tabela).")

    # Adicionar um campo de exemplo (opcional)
    campo_nome = ogr.FieldDefn("nome", ogr.OFTString)
    campo_nome.SetWidth(100)
    layer.CreateField(campo_nome)

    print(f"Tabela '{nome_tabela}' com geometria '{tipo_geom}' criada com sucesso em {nome_banco}.")

    # Fechar o datasource
    ds.Destroy()

# Exemplo de uso
if __name__ == "__main__":
    criar_tabela_postgis(
        nome_tabela="meus_pontos",
        tipo_geometria="POINT",
        nome_banco="meu_banco",
        usuario="meu_usuario",
        senha="minha_senha"
    )

