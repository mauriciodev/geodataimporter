import os

from dotenv import load_dotenv
from osgeo import ogr

load_dotenv()

databaseServer = "localhost"
databaseName = "escala"
databaseUser = "postgres"
databasePW = os.getenv("senha")


connString = "PG: host=%s dbname=%s user=%s password=%s" % (
    databaseServer,
    databaseName,
    databaseUser,
    databasePW,
)

conn = ogr.Open(connString)

# exemplo para testar o funcionamento
layerList = []
for layer in conn:
    daLayer = layer.GetName()
    if not daLayer in layerList:
        layerList.append(daLayer)

layerList.sort()

for j in layerList:
    print(j)

# Close connection
conn = None

daShapefile = r"/vsizip//home/mauricio/Desktop/Pesquisa/PFC_2025/g04_na19.zip"

dataSource = ogr.Open(daShapefile)
daLayer = dataSource.GetLayer(0)
layerDefinition = daLayer.GetLayerDefn()  # obtem as definições dos atributos


for i in range(layerDefinition.GetFieldCount()):
    print(layerDefinition.GetFieldDefn(i).GetName())
