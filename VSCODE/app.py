import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from pathlib import Path

# 1. Configuração inicial da página
st.set_page_config(page_title="Dossiê BHRC", layout="wide")
st.title("💧 Dossiê Interativo: Bacia Hidrográfica do Rio do Carmo")
st.markdown("Análise espacial dos Sistemas Ambientais e Ecodinâmica.")

# 2. O RADAR AUTOMÁTICO DE ARQUIVOS
BASE_DIR = Path(__file__).resolve().parent

# Identifica a raiz do repositório, não importa se o app.py está na raiz ou na pasta VSCODE
REPO_DIR = BASE_DIR.parent if BASE_DIR.name == "VSCODE" else BASE_DIR

# Varre TODAS as pastas e subpastas do seu GitHub procurando qualquer arquivo .geojson
# O .lower() garante que ele ache mesmo se a extensão estiver como .GeoJSON
todos_arquivos = [f for f in REPO_DIR.rglob("*") if f.suffix.lower() == '.geojson']

if not todos_arquivos:
    st.error("⚠️ O servidor não encontrou nenhum arquivo '.geojson' no seu repositório!")
    st.warning("Solução: Verifique no seu GitHub se os arquivos dos mapas realmente terminaram de fazer o upload.")
    st.stop()

# 3. Cria o menu dinamicamente baseado no que ele achou
mapas_encontrados = {}
for arquivo in sorted(todos_arquivos):
    # Transforma o nome feio do arquivo em um nome bonito para o menu
    nome_legivel = arquivo.stem.replace("dados_ppgeo_bh_", "").replace("_", " ").title()
    # Ajustes finos para siglas
    nome_legivel = nome_legivel.replace("Ana", "ANA").replace("Map Biomas", "MapBiomas")
    
    mapas_encontrados[nome_legivel] = arquivo

# 4. Barra Lateral (Menu de Seleção)
st.sidebar.header("Inventário Biofísico")
tema_selecionado = st.sidebar.radio("Selecione o Mapa Temático:", list(mapas_encontrados.keys()))

# 5. Função inteligente para carregar apenas o arquivo selecionado
@st.cache_data(show_spinner=False)
def carregar_mapa(caminho_arquivo: str): 
    return gpd.read_file(caminho_arquivo)

# Executa a leitura
caminho_do_mapa = mapas_encontrados[tema_selecionado]
try:
    gdf = carregar_mapa(str(caminho_do_mapa))
except Exception:
    st.error(f"⚠️ Erro ao processar as geometrias do arquivo {caminho_do_mapa.name}.")
    st.stop()

# 6. Construindo o Mapa Interativo
st.subheader(f"Mapa Interativo: {tema_selecionado}")

# Calcula o centro para focar na bacia automaticamente
centro_y = gdf.geometry.centroid.y.mean()
centro_x = gdf.geometry.centroid.x.mean()

m = folium.Map(location=[centro_y, centro_x], zoom_start=9, tiles="CartoDB positron")

# Identifica automaticamente qual coluna tem as classes para colorir o mapa
coluna_id = next((col for col in gdf.columns if col.lower() in {"id", "codigo", "cod", "cd", "gid"}), gdf.columns[0])
coluna_classe = next((col for col in gdf.columns if col.upper() == "CLASSE"), None)

if coluna_classe is None:
    coluna_classe = next((col for col in gdf.columns if col not in {coluna_id, "geometry"}), None)
if coluna_classe is None:
    coluna_classe = gdf.columns[0]

# Adiciona as camadas e renderiza
folium.Choropleth(
    geo_data=gdf,
    data=gdf,
    columns=[coluna_id, coluna_classe],
    key_on=f'feature.properties.{coluna_id}',
    fill_color="YlGnBu",
    fill_opacity=0.7,
    line_opacity=0.3,
    legend_name=tema_selecionado,
).add_to(m)

folium.GeoJsonTooltip(fields=[coluna_classe]).add_to(
    folium.GeoJson(gdf, style_function=lambda x: {"color": "transparent", "fillColor": "transparent"})
).add_to(m)

st_folium(m, width=1000, height=600)
