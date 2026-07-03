import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from pathlib import Path

# 1. Configuração inicial da página
st.set_page_config(page_title="Dossiê BHRC", layout="wide")
st.title("💧 Dossiê Interativo: Bacia Hidrográfica do Rio do Carmo")
st.markdown("Análise espacial dos Sistemas Ambientais e Ecodinâmica.")

# 2. A MÁGICA DA CORREÇÃO DE CAMINHOS:
BASE_DIR = Path(__file__).resolve().parent  # Isso aponta para a pasta VSCODE
DATA_DIR = BASE_DIR.parent / "data"         # O '.parent' faz o código "voltar" uma pasta e achar a 'data'

# 3. Dicionário mapeando a escolha do usuário para o arquivo correto
mapas_disponiveis = {
    "Afloramentos": DATA_DIR / "dados_ppgeo_bh_afloramentos.geojson",
    "Bacia Delimitação": DATA_DIR / "dados_ppgeo_bh_bacia_delimitacao.geojson",
    "Balanço Hídrico": DATA_DIR / "dados_ppgeo_bh_balanco_hidrico.geojson",
    "Clima": DATA_DIR / "dados_ppgeo_bh_clima.geojson",
    "Declividade": DATA_DIR / "dados_ppgeo_bh_declividade.geojson",
    "Drenagem ANA": DATA_DIR / "dados_ppgeo_bh_drenagem_ANA.geojson",
    "Estações": DATA_DIR / "dados_ppgeo_bh_estacoes.geojson",
    "Estruturas": DATA_DIR / "dados_ppgeo_bh_estruturas.geojson",
    "Geologia": DATA_DIR / "dados_ppgeo_bh_geologia.geojson",
    "Geomorfologia": DATA_DIR / "dados_ppgeo_bh_geomorfologia.geojson",
    "Massa d'Água": DATA_DIR / "dados_ppgeo_bh_massa_dagua.geojson",
    "Municípios": DATA_DIR / "dados_ppgeo_bh_municipios.geojson",
    "Rio Carmo Curso": DATA_DIR / "dados_ppgeo_bh_rio_carmo_curso.geojson",
    "Tipos de Solos (Pedologia)": DATA_DIR / "dados_ppgeo_bh_tipos_solos_pedologia.geojson",
    "Uso e Cobertura do Solo": DATA_DIR / "dados_ppgeo_bh_uso_cobertura_solo.geojson",
    "Uso do Solo MapBiomas": DATA_DIR / "dados_ppgeo_bh_uso_solo_MAP_BIOMAS.geojson",
    "Vegetação": DATA_DIR / "dados_ppgeo_bh_vegetacao.geojson",
    "Vulnerabilidade Ambiental": DATA_DIR / "dados_ppgeo_bh_vulnerabilidade_ambiental.geojson",
    "Vulnerabilidade Natural": DATA_DIR / "dados_ppgeo_bh_vulnerabilidade_natural.geojson"
}

# Verifica se os arquivos realmente existem na pasta antes de colocar no menu
mapas_encontrados = {nome: caminho for nome, caminho in mapas_disponiveis.items() if caminho.exists()}

if not mapas_encontrados:
    st.error(f"⚠️ Nenhum arquivo encontrado no caminho: {DATA_DIR}. Verifique o repositório.")
    st.stop()

# 4. Barra Lateral (Menu de Seleção)
st.sidebar.header("Inventário Biofísico")
tema_selecionado = st.sidebar.radio("Selecione o Mapa Temático:", list(mapas_encontrados.keys()))

# 5. Função inteligente para carregar apenas o arquivo selecionado
@st.cache_data(show_spinner=False)
def carregar_mapa(caminho_arquivo: str): 
    return gpd.read_file(caminho_arquivo)

# Pega o caminho do arquivo baseado na escolha do menu
caminho = mapas_encontrados[tema_selecionado]
try:
    gdf = carregar_mapa(str(caminho))
except Exception:
    st.error(f"⚠️ Erro ao carregar o arquivo {caminho.name}.")
    st.stop()

# 6. Construindo o Mapa Interativo
st.subheader(f"Mapa Interativo: {tema_selecionado}")

# Calculando o centro dinamicamente para focar na bacia
centro_y = gdf.geometry.centroid.y.mean()
centro_x = gdf.geometry.centroid.x.mean()

# Criando o mapa base
m = folium.Map(location=[centro_y, centro_x], zoom_start=9, tiles="CartoDB positron")

# Descobrindo quais colunas usar para identificar e colorir os dados
coluna_id = next((col for col in gdf.columns if col.lower() in {"id", "codigo", "cod", "cd", "gid"}), gdf.columns[0])
coluna_classe = next((col for col in gdf.columns if col.upper() == "CLASSE"), None)

if coluna_classe is None:
    coluna_classe = next((col for col in gdf.columns if col not in {coluna_id, "geometry"}), None)
if coluna_classe is None:
    coluna_classe = gdf.columns[0]

# Adicionando os polígonos ao mapa
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

# Adicionando tooltips (caixa de texto ao passar o mouse)
folium.GeoJsonTooltip(fields=[coluna_classe]).add_to(
    folium.GeoJson(gdf, style_function=lambda x: {"color": "transparent", "fillColor": "transparent"})
).add_to(m)

# Renderizando no Streamlit
st_folium(m, width=1000, height=600)
