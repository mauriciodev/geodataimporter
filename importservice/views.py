from django.utils import timezone
from rest_framework import generics, viewsets, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.conf import settings
import os
import psycopg2
from urllib.parse import unquote_plus

from .models import HistoricoImportacaoExclusao, ProdutoGeoespacial, RepresentacaoGrafica
from .serializers import HistoricoImportacaoExclusaoSerializer, ProdutoGeoespacialSerializer, RepresentacaoGraficaSerializer
from . import ogr_importer


# ------------------------ UPLOAD ------------------------
class UploadArquivoView(APIView):
    parser_classes = [MultiPartParser]

    @swagger_auto_schema(
        operation_description="Upload de múltiplos arquivos GPKG, ZIP, SHP ou XML para importação via OGR.",
        manual_parameters=[
            openapi.Parameter(
                name="arquivos",
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description="Envie múltiplos arquivos vetoriais (GPKG, ZIP, SHP ou XML)",
                required=True,
                multiple=True
            )
        ],
        responses={200: "Arquivos importados ou ignorados com aviso"}
    )
    def post(self, request, format=None):
        arquivos = request.FILES.getlist("arquivos")
        if not arquivos:
            return Response({"erro": "Nenhum arquivo enviado"}, status=status.HTTP_400_BAD_REQUEST)

        pasta_destino = os.path.join(settings.MEDIA_ROOT, "uploads")
        os.makedirs(pasta_destino, exist_ok=True)

        conn_str = "PG: " + ' '.join(f"{k}={v}" for k, v in ogr_importer.CONFIG_BANCO.items())
        ogr_importer.verificar_ou_criar_tabela(ogr_importer.TABELA_GLOBAL, conn_str)

        resultados = []

        try:
            conn = psycopg2.connect(
                dbname=ogr_importer.CONFIG_BANCO["dbname"],
                user=ogr_importer.CONFIG_BANCO["user"],
                password=ogr_importer.CONFIG_BANCO["password"],
                host=ogr_importer.CONFIG_BANCO["host"],
                port=ogr_importer.CONFIG_BANCO["port"],
            )
            cursor = conn.cursor()
        except Exception as e:
            return Response({"erro": f"Erro ao conectar no banco para pré-verificação: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        for arquivo in arquivos:
            nome = arquivo.name
            caminho_salvo = os.path.join(pasta_destino, nome)

            with open(caminho_salvo, "wb+") as destino:
                for chunk in arquivo.chunks():
                    destino.write(chunk)

            xml_path = ogr_importer.find_xml_for_file(caminho_salvo)
            escala, data_do_produto, esquema, metadata_id = ogr_importer.extract_metadata_from_xml(xml_path)

            if not metadata_id:
                metadata_id = os.path.splitext(nome)[0]

            # Verifica se já existe feições com esse metadata_id
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {ogr_importer.TABELA_GLOBAL} WHERE metadata_id = %s", (metadata_id,))
                count = cursor.fetchone()[0]
            except Exception as e:
                resultados.append({
                    "arquivo": nome,
                    "status": "erro",
                    "detalhes": f"Erro ao verificar existência no banco: {str(e)}"
                })
                continue

            if count > 0:
                resultados.append({
                    "arquivo": nome,
                    "status": "aviso",
                    "detalhes": f"Arquivo com metadata_id '{metadata_id}' já existe no banco. Importação ignorada."
                })
                continue  # Não importa, nem registra histórico

            # Importa só se não existir
            try:
                ogr_importer.importar_para_tabela(
                    caminho_salvo,
                    ogr_importer.TABELA_GLOBAL,
                    xml=xml_path
                )

                HistoricoImportacaoExclusao.objects.create(
                    metadata_id=metadata_id,
                    classe=None,
                    acao='adicionado',
                    usuario=request.user if request.user.is_authenticated else None,
                    detalhes=f"Arquivo {nome} importado com sucesso."
                )

                resultados.append({
                    "arquivo": nome,
                    "status": "sucesso",
                    "metadata_id": metadata_id
                })

            except Exception as e:
                ogr_importer.safe_print(f"Erro ao importar {nome}: {e}")
                resultados.append({
                    "arquivo": nome,
                    "status": "erro",
                    "detalhes": str(e)
                })

        cursor.close()
        conn.close()

        return Response(resultados)


# ------------------------ REMOVER ------------------------
class RemoverProdutoView(APIView):
    @swagger_auto_schema(
        operation_description="Remove feições por metadata_id. Opcionalmente, filtra por classe.",
        manual_parameters=[
            openapi.Parameter(
                "classe",
                openapi.IN_QUERY,
                description="Classe específica para remoção dentro do metadata_id",
                type=openapi.TYPE_STRING
            )
        ]
    )
    def delete(self, request, metadata_id):
        classe = request.query_params.get("classe", None)

        try:
            conn = psycopg2.connect(
                dbname=ogr_importer.CONFIG_BANCO["dbname"],
                user=ogr_importer.CONFIG_BANCO["user"],
                password=ogr_importer.CONFIG_BANCO["password"],
                host=ogr_importer.CONFIG_BANCO["host"],
                port=ogr_importer.CONFIG_BANCO["port"],
            )
            cursor = conn.cursor()

            if classe:
                sql = f"DELETE FROM {ogr_importer.TABELA_GLOBAL} WHERE metadata_id = %s AND classe = %s"
                cursor.execute(sql, (metadata_id, classe))
            else:
                sql = f"DELETE FROM {ogr_importer.TABELA_GLOBAL} WHERE metadata_id = %s"
                cursor.execute(sql, (metadata_id,))

            conn.commit()

            if cursor.rowcount == 0:
                msg = f"Nenhuma feição encontrada para metadata_id '{metadata_id}'"
                if classe:
                    msg += f" e classe '{classe}'"
                cursor.close()
                conn.close()
                return Response({"mensagem": msg}, status=status.HTTP_404_NOT_FOUND)

            msg = f"Feições com metadata_id '{metadata_id}'"
            if classe:
                msg += f" e classe '{classe}'"
            msg += " removidas com sucesso."

            # só registra histórico se realmente removeu
            HistoricoImportacaoExclusao.objects.create(
                metadata_id=metadata_id,
                classe=classe,
                acao='removido',
                usuario=request.user if request.user.is_authenticated else None,
                detalhes=msg
            )

            cursor.close()
            conn.close()

            return Response({"mensagem": msg})

        except Exception as e:
            ogr_importer.safe_print(f"Erro ao remover {metadata_id}: {e}")
            return Response({"erro": f"Erro ao remover: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------------ LISTAR PRODUTOS ------------------------
class ListarProdutosView(APIView):
    @swagger_auto_schema(
        operation_description="Lista produtos importados. Filtra opcionalmente por metadata_id e classe.",
        manual_parameters=[
            openapi.Parameter("metadata_id", openapi.IN_QUERY, description="Filtra por metadata_id", type=openapi.TYPE_STRING),
            openapi.Parameter("classe", openapi.IN_QUERY, description="Filtra por classe", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request):
        filtro_metadata = request.query_params.get("metadata_id", None)
        filtro_classe = request.query_params.get("classe", None)

        try:
            conn = psycopg2.connect(
                dbname=ogr_importer.CONFIG_BANCO["dbname"],
                user=ogr_importer.CONFIG_BANCO["user"],
                password=ogr_importer.CONFIG_BANCO["password"],
                host=ogr_importer.CONFIG_BANCO["host"],
                port=ogr_importer.CONFIG_BANCO["port"],
            )
            cursor = conn.cursor()

            sql = f"""
                SELECT metadata_id, classe, escala, data_do_produto, esquema,
                       json_agg(json::json) AS jsons
                FROM {ogr_importer.TABELA_GLOBAL}
                WHERE 1=1
            """
            params = []

            if filtro_metadata:
                sql += " AND metadata_id = %s"
                params.append(unquote_plus(filtro_metadata))
            if filtro_classe:
                sql += " AND classe = %s"
                params.append(unquote_plus(filtro_classe))

            sql += " GROUP BY metadata_id, classe, escala, data_do_produto, esquema ORDER BY metadata_id;"

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            produtos = []
            for row in rows:
                produtos.append({
                    "metadata_id": row[0],
                    "classe": row[1],
                    "escala": row[2],
                    "data_do_produto": row[3],
                    "esquema": row[4],
                    "jsons": row[5]
                })

            cursor.close()
            conn.close()

            return Response(produtos)

        except Exception as e:
            ogr_importer.safe_print(f"Erro ao listar produtos: {e}")
            return Response({"erro": f"Erro ao listar produtos: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------------ HISTÓRICO ------------------------
class ListarHistoricoView(APIView):
    def get(self, request):
        try:
            historico = HistoricoImportacaoExclusao.objects.all().order_by('-data_evento')[:200]
            serializer = HistoricoImportacaoExclusaoSerializer(historico, many=True)
            return Response(serializer.data)
        except Exception as e:
            ogr_importer.safe_print(f"Erro ao listar histórico: {e}")
            return Response({"erro": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ------------------------ API ROOT ------------------------
class ApiRootView(APIView):
    def get(self, request):
        return Response({
            "mensagem": "API Geodataimporter funcionando.",
            "endpoints": {
                "importar": "/api/importar/",
                "remover": "/api/remover/{metadata_id}/",
                "produtos": "/api/produtos/",
                "historico-importacoes": "/api/historico-importacoes/",
                "representacao-grafica": "/api/representacao-grafica/",
                "representacao-grafica-bulk": "/api/representacao-grafica/bulk-update/"
            }
        })


# ------------------------ REPRESENTAÇÃO GRÁFICA ------------------------
class RepresentacaoGraficaListCreateView(generics.ListCreateAPIView):
    queryset = RepresentacaoGrafica.objects.all()
    serializer_class = RepresentacaoGraficaSerializer

class RepresentacaoGraficaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = RepresentacaoGrafica.objects.all()
    serializer_class = RepresentacaoGraficaSerializer

class RepresentacaoGraficaBulkUpdateView(APIView):
    @swagger_auto_schema(
        operation_description="Atualização em massa dos grupos de representação gráfica",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'esquema': openapi.Schema(type=openapi.TYPE_STRING),
                    'classe': openapi.Schema(type=openapi.TYPE_STRING),
                    'grupo_representacao': openapi.Schema(type=openapi.TYPE_STRING),
                }
            )
        )
    )
    def put(self, request):
        data = request.data
        resultados = []
        
        for item in data:
            try:
                if item['grupo_representacao'] not in dict(RepresentacaoGrafica.TIPO_GRUPO_CHOICES):
                    raise ValueError(f"Grupo de representação inválido: {item['grupo_representacao']}")

                obj, created = RepresentacaoGrafica.objects.update_or_create(
                    esquema=item['esquema'],
                    classe=item['classe'],
                    defaults={'grupo_representacao': item['grupo_representacao']}
                )
                
                resultados.append({
                    'esquema': item['esquema'],
                    'classe': item['classe'],
                    'status': 'criado' if created else 'atualizado',
                    'grupo_representacao': obj.grupo_representacao
                })
                
            except Exception as e:
                resultados.append({
                    'esquema': item.get('esquema'),
                    'classe': item.get('classe'),
                    'status': 'erro',
                    'erro': str(e)
                })
        
        return Response(resultados)


# ------------------------ VIEWSETS ------------------------
class ProdutoGeoespacialViewSet(viewsets.ModelViewSet):
    queryset = ProdutoGeoespacial.objects.all()
    serializer_class = ProdutoGeoespacialSerializer

class RepresentacaoGraficaViewSet(viewsets.ModelViewSet):
    queryset = RepresentacaoGrafica.objects.all()
    serializer_class = RepresentacaoGraficaSerializer

class HistoricoImportacaoExclusaoViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HistoricoImportacaoExclusao.objects.all().order_by('-data_evento')
    serializer_class = HistoricoImportacaoExclusaoSerializer
