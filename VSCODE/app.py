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
REPO_DIR = BASE_DIR.parent if BASE_DIR.name == "VSCODE" else BASE_DIR

todos_arquivos = [f for f in REPO_DIR.rglob("*") if f.suffix.lower() == '.geojson']

if not todos_arquivos:
    st.error("⚠️ O servidor não encontrou nenhum arquivo '.geojson' no seu repositório!")
    st.stop()

# 3. Cria a lista de camadas disponíveis
mapas_encontrados = {}
for arquivo in sorted(todos_arquivos):
    nome_legivel = arquivo.stem.replace("dados_ppgeo_bh_", "").replace("_", " ").title()
    nome_legivel = nome_legivel.replace("Ana", "ANA").replace("Map Biomas", "MapBiomas")
    mapas_encontrados[nome_legivel] = arquivo

# 4. Barra Lateral - MÚLTIPLA ESCOLHA (A lógica correta de SIG)
st.sidebar.header("Painel de Camadas")
st.sidebar.markdown("Selecione múltiplas camadas para sobrepor no mapa:")

camadas_selecionadas = st.sidebar.multiselect(
    "Camadas disponíveis:", 
    list(mapas_encontrados.keys()),
    default=[list(mapas_encontrados.keys())[0]] # Já deixa a primeira camada ligada por padrão
)

# 5. Função inteligente e limpa para carregar o mapa
@st.cache_data(show_spinner=False)
def carregar_mapa(caminho_arquivo: str): 
    return gpd.read_file(caminho_arquivo)

# 6. Construindo o Mapa Base
st.subheader("Visualizador de Mapas Web")

# Centralizado nas coordenadas aproximadas da região do semiárido potiguar
m = folium.Map(location=[-5.5, -37.5], zoom_start=9, tiles="CartoDB positron")

# Paleta de cores para diferenciar as camadas que forem sendo ligadas
cores = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#a65628', '#1b9e77']

# 7. Iterando sobre cada camada que o usuário escolheu
if camadas_selecionadas:
    for idx, nome_camada in enumerate(camadas_selecionadas):
        caminho_do_mapa = mapas_encontrados[nome_camada]
        
        try:
            gdf = carregar_mapa(str(caminho_do_mapa))
        except Exception:
            st.sidebar.error(f"⚠️ Falha ao ler geometria de {nome_camada}.")
            continue
            
        # Garante que os dados estejam em WGS 84 (padrão web) para não sumirem da tela
        if gdf.crs is not None and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        cor_da_camada = cores[idx % len(cores)]

        # Prepara um Tooltip simples com as duas primeiras colunas (ignorando a geometria)
        colunas_validas = [col for col in gdf.columns if col != 'geometry']
        colunas_tooltip = colunas_validas[:2] if colunas_validas else None

        # Cria um "FeatureGroup" - Isso permite que a camada apareça no menu do Leaflet
        fg = folium.FeatureGroup(name=nome_camada)

        # Adiciona a geometria pura da camada
        folium.GeoJson(
            gdf,
            name=nome_camada,
            style_function=lambda feature, color=cor_da_camada: {
                'fillColor': color,
                'color': color,
                'weight': 1.5,
                'fillOpacity': 0.5
            },
            tooltip=folium.GeoJsonTooltip(fields=colunas_tooltip) if colunas_tooltip else None
        ).add_to(fg)

        # Adiciona o grupo ao mapa base
        fg.add_to(m)

# 8. Adiciona o controle de camadas nativo do Leaflet (A cereja do bolo)
folium.LayerControl(collapsed=False).add_to(m)

# Renderiza no Streamlit
st_folium(m, width=1000, height=600)
