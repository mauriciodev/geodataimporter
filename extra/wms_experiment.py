import time
from io import BytesIO
from typing import List, Tuple, Dict
from owslib.wms import WebMapService
import numpy as np
from PIL import Image
import pandas as pd
import matplotlib.pyplot as plt

server_url = "http://localhost/qgis"
wms = WebMapService(server_url, version='1.1.1')

# Criar varias bounding boxes
# criar uma funcao que 
#Calcular histograma (media, devio padrao)
bbox_master = (-43.768612, -21.7635, -43.4915, -21.2421)

def controle_de_tempo(bbox)
    start_time = time.time()  # or time.perf_counter() for higher precision
    img = wms.getmap(   layers=['importacao_geometrias'],
                        srs='EPSG:4326',
                        bbox=bbox,
                        size=(256, 256),
                        format='image/png',
                        transparent=True)
    end_time = time.time()  # or time.perf_counter()
    elapsed_time = end_time - start_time
    return elapsed_time

#out = open('jpl_mosaic_visb.jpg', 'wb')
#out.write(img.read())
#out.close()

print(f"Elapsed Time: {elapsed_time:.4f} seconds")