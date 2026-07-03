import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium

# 1. Configuração inicial da página
st.set_page_config(page_title="Dossiê BHRC", layout="wide")
st.title("💧 Dossiê Interativo: Bacia Hidrográfica do Rio do Carmo")
st.markdown("Análise espacial dos Sistemas Ambientais e Ecodinâmica.")

# 2. Dicionário mapeando a escolha do usuário para o arquivo correto
mapas_disponiveis = {
    "Afloramentos": "data/dados_ppgeo_bh_afloramentos.geojson",
    "Bacia Delimitação": "data/dados_ppgeo_bh_bacia_delimitacao.geojson",
    "Balanço Hídrico": "data/dados_ppgeo_bh_balanco_hidrico.geojson",
    "Clima": "data/dados_ppgeo_bh_clima.geojson",
    "Drenagem ANA": "data/dados_ppgeo_bh_drenagem_ANA.geojson",
    "Estações": "data/dados_ppgeo_bh_estacoes.geojson",
    "Estruturas": "data/dados_ppgeo_bh_estruturas.geojson",
    "Geologia": "data/dados_ppgeo_bh_geologia.geojson",
    "Geomorfologia": "data/dados_ppgeo_bh_geomorfologia.geojson",
    "Massa d'Água": "data/dados_ppgeo_bh_massa_dagua.geojson",
    "Municípios": "data/dados_ppgeo_bh_municipios.geojson",
    "Rio Carmo Curso": "data/dados_ppgeo_bh_rio_carmo_curso.geojson",
    "Tipos de Solos (Pedologia)": "data/dados_ppgeo_bh_tipos_solos_pedologia.geojson",
    "Vegetação": "data/dados_ppgeo_bh_vegetacao.geojson",
    "Vulnerabilidade Ambiental": "data/dados_ppgeo_bh_vulnerabilidade_ambiental.geojson",
    "Vulnerabilidade Natural": "data/dados_ppgeo_bh_vulnerabilidade_natural.geojson"
}

# 3. Barra Lateral (Menu de Seleção)
st.sidebar.header("Inventário Biofísico")
tema_selecionado = st.sidebar.radio("Selecione o Mapa Temático:", list(mapas_disponiveis.keys()))

# 4. Função inteligente para carregar apenas o arquivo selecionado
@st.cache_data
def carregar_mapa(caminho_arquivo):
    return gpd.read_file(caminho_arquivo)

# Pega o caminho do arquivo baseado na escolha do menu e carrega o GeoDataFrame
caminho = mapas_disponiveis[tema_selecionado]
try:
    gdf = carregar_mapa(caminho)
except Exception as e:
    st.error(f"⚠️ Erro ao carregar o arquivo {caminho}. Verifique se ele está na pasta 'data'.")
    st.stop()

# 5. Construindo o Mapa Interativo
st.subheader(f"Mapa Interativo: {tema_selecionado}")

# Calculando o centro dinamicamente para focar na bacia
centro_y = gdf.geometry.centroid.y.mean()
centro_x = gdf.geometry.centroid.x.mean()

# Criando o mapa base
m = folium.Map(location=[centro_y, centro_x], zoom_start=9, tiles="CartoDB positron")

# Descobrindo qual coluna usar para a cor (Pode precisar de ajuste dependendo das suas tabelas)
# Aqui, assumimos que a coluna que tem a classificação se chama 'CLASSE'
coluna_classe = 'CLASSE' if 'CLASSE' in gdf.columns else gdf.columns[0]

# Adicionando os polígonos ao mapa
folium.Choropleth(
    geo_data=gdf,
    data=gdf,
    columns=[gdf.columns[0], coluna_classe], 
    key_on=f'feature.properties.{gdf.columns[0]}',
    fill_color='YlGnBu', # Você pode customizar as cores depois para cada tema
    fill_opacity=0.7,
    line_opacity=0.3,
    legend_name=tema_selecionado
).add_to(m)

# Adicionando tooltips (caixa de texto ao passar o mouse)
folium.GeoJsonTooltip(fields=[coluna_classe]).add_to(
    folium.GeoJson(gdf, style_function=lambda x: {'color': 'transparent', 'fillColor': 'transparent'})
).add_to(m)

# Renderizando no Streamlit
st_folium(m, width=1000, height=600)
