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

# --- A SOLUÇÃO CARTOGRÁFICA PARA MAPAS CATEGÓRICOS ---
# 1. Uma paleta de cores forte e distinta para as diferentes unidades de paisagem e sistemas
paleta_cores = [
    '#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', 
    '#ffff33', '#a65628', '#f781bf', '#1b9e77', '#d95f02', '#7570b3'
]

# 2. Criamos um dicionário vinculando cada classe de texto a uma cor fixa
classes_unicas = gdf[coluna_classe].astype(str).unique()
mapa_cores = {classe: paleta_cores[i % len(paleta_cores)] for i, classe in enumerate(classes_unicas)}

# 3. Desenhamos os polígonos aplicando as cores categóricas individuais
camada_tematica = folium.GeoJson(
    gdf,
    style_function=lambda feature: {
        # Busca a cor da classe. Se não achar, pinta de cinza
        'fillColor': mapa_cores.get(str(feature['properties'].get(coluna_classe, '')), '#999999'),
        'color': 'black',        # Cor da borda do polígono
        'weight': 0.5,           # Espessura da borda
        'fillOpacity': 0.7,      # Transparência
    }
)

# 4. Adicionamos a caixinha interativa (Tooltip) que aparece ao passar o mouse
folium.GeoJsonTooltip(
    fields=[coluna_classe],
    aliases=[f"Classe/Categoria: "],
    style=("background-color: white; color: #333333; font-family: arial; font-size: 13px; padding: 10px;")
).add_to(camada_tematica)

# 5. Anexa a camada processada ao mapa base
camada_tematica.add_to(m)

# Renderiza o mapa final na tela
st_folium(m, width=1000, height=600)
