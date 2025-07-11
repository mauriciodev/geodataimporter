## 🗺️ GeoData Importer

Este projeto visa desenvolver um sistema de importação, armazenamento e padronização de dados vetoriais geoespaciais em banco de dados PostGIS, permitindo integrar diferentes estruturas como EDGV 2.1.3, EDGV 3.0 e modelagens do IBGE. O sistema extrai metadados, converte atributos para objetos JSON e organiza as geometrias de forma normalizada, apoiando a interoperabilidade e exibição em servidores de mapas.

---

## 🛠️ Requisitos do Sistema

Antes de rodar o projeto, verifique se seu ambiente atende aos seguintes pré-requisitos:

- **Python 3.8 ou superior**  
  Instale pelo [site oficial](https://www.python.org/downloads/) ou via gerenciador de pacotes da sua distribuição.

- **Bibliotecas Python**  
  Instaladas automaticamente via `conda' pelo arquivo `requirements.txt`:
  - `python-dotenv==1.1.0`
  - `gdal==3.1.1`

- **PostgreSQL com extensão PostGIS ativada**  
  Banco de dados espacial necessário para armazenar os dados vetoriais.  
  Pode-se instalar o PostgreSQL e adicionar a extensão PostGIS conforme a documentação oficial:  
  [https://postgis.net/install/](https://postgis.net/install/)

---

## 📂 Estrutura esperada dos arquivos

A pasta definida na variável `PASTA_ARQUIVOS` deve conter arquivos:

- `.gpkg` (Geopackage) ou `.zip` contendo shapefiles  
- Arquivos `.xml` com o mesmo nome base, contendo os metadados (opcional, mas recomendado para mais informações)

---

## ⚙️ Configuração

### 1. Clone o repositório

```bash
git clone https://github.com/seu_usuario/seu_repositorio.git
cd seu_repositorio

## 2 Ambiente virtual (recomendado que crie um)

python -m venv venv
# Ative:
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

## 3 Instale as dependências
conda create --name geoenv --file requirements.txt

## 4 Configuração do .env
# Copie o exemplo:
cp .env.example .env  # Linux/macOS
copy .env.example .env  # Windows
# Após isso, edite o novo .env com seus dados reais.

## 5 Execute o script de importação
python ogr_importer.py