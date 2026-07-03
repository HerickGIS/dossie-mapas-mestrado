import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from pathlib import Path

# 1. Configuração inicial da página
st.set_page_config(page_title="Dossiê BHRC", layout="wide", initial_sidebar_state="expanded")

# 2. Cabeçalho e Título
st.title("💧 Dossiê Interativo: Bacia Hidrográfica do Rio do Carmo")
st.markdown("**Análise Espacial dos Sistemas Ambientais e Ecodinâmica com base na metodologia de Jean Tricart.**")

# --- MÓDULO DE FUNDAMENTAÇÃO METODOLÓGICA ---
with st.expander("📖 Metodologia e Modelagem Espacial (Clique para expandir)", expanded=False):
    st.markdown("""
    A análise de vulnerabilidade desta bacia baseia-se nos princípios da **Ecodinâmica de Tricart (1977)**, que avalia a relação entre os processos de pedogênese (formação do solo) e morfogênese (degradação).
    
    A modelagem em Sistema de Informação Geográfica (SIG) foi realizada por meio de Álgebra de Mapas, integrando cinco variáveis biofísicas: **Geomorfologia, Geologia, Pedologia, Vegetação e Uso e Cobertura da Terra**.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Vulnerabilidade Natural (VN)")
        st.markdown("Avalia a suscetibilidade intrínseca do meio físico, calculada pela média aritmética dos pesos atribuídos às classes de cada variável biofísica.")
        st.latex(r"VN = \frac{Geomorfologia + Geologia + Pedologia + Vegetação + Uso\ da\ Terra}{5}")
        
    with col2:
        st.subheader("Vulnerabilidade Ambiental (VA)")
        st.markdown("Insere o peso da pressão antrópica sobre o meio físico. O fator 'Uso e Cobertura da Terra' recebe o peso dominante (0.5), evidenciando o impacto humano na degradação da bacia.")
        st.latex(r"VA = 0.2 \times [Geomorfologia] + 0.1 \times [Geologia] + 0.1 \times [Pedologia] + 0.1 \times [Vegetação] + 0.5 \times [Uso\ e\ Cobertura]")
# --------------------------------------------

# 3. O RADAR AUTOMÁTICO DE ARQUIVOS
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent if BASE_DIR.name == "VSCODE" else BASE_DIR

todos_arquivos = [f for f in REPO_DIR.rglob("*") if f.suffix.lower() == '.geojson']

if not todos_arquivos:
    st.error("⚠️ O servidor não encontrou nenhum arquivo '.geojson' no seu repositório!")
    st.stop()

# 4. Cria a lista de camadas disponíveis
mapas_encontrados = {}
for arquivo in sorted(todos_arquivos):
    nome_legivel = arquivo.stem.replace("dados_ppgeo_bh_", "").replace("_", " ").title()
    nome_legivel = nome_legivel.replace("Ana", "ANA").replace("Map Biomas", "MapBiomas")
    mapas_encontrados[nome_legivel] = arquivo

# 5. DICIONÁRIOS DE CORES CARTOGRÁFICAS
cores_vulnerabilidade = {
    'Muito Baixa': '#1a9850',       
    'Baixa': '#91cf60',             
    'Média': '#fee08b',             
    'Alta': '#fc8d59',              
    'Muito Alta': '#d73027',        
    'Sem Classificação': '#969696', 
    'Sem classificacao': '#969696'
}
paleta_generica = ['#377eb8', '#984ea3', '#ff7f00', '#a65628', '#f781bf']

# 6. Barra Lateral - SELEÇÃO E EXPLICAÇÕES DINÂMICAS
st.sidebar.header("Painel de Camadas")
camadas_selecionadas = st.sidebar.multiselect(
    "Selecione as variáveis para o mapa:", 
    list(mapas_encontrados.keys()),
    default=["Vulnerabilidade Natural"] if "Vulnerabilidade Natural" in mapas_encontrados else [list(mapas_encontrados.keys())[0]]
)

# Textos dinâmicos na barra lateral baseados na seleção
if "Vulnerabilidade Ambiental" in camadas_selecionadas:
    st.sidebar.info("**Nota:** O mapa de Vulnerabilidade Ambiental exibe forte influência do Uso da Terra (Peso 50%).")
if "Vulnerabilidade Natural" in camadas_selecionadas:
    st.sidebar.success("**Nota:** O mapa de Vulnerabilidade Natural reflete o equilíbrio morfo-pedológico (Média simples).")

@st.cache_data(show_spinner=False)
def carregar_mapa(caminho_arquivo: str): 
    return gpd.read_file(caminho_arquivo)

# 7. Construindo o Mapa Base
st.subheader("Visualizador Cartográfico")
m = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles="CartoDB positron")

# 8. Lógica de renderização e análise
if camadas_selecionadas:
    for idx, nome_camada in enumerate(camadas_selecionadas):
        caminho_do_mapa = mapas_encontrados[nome_camada]
        
        try:
            gdf = carregar_mapa(str(caminho_do_mapa))
        except Exception:
            st.sidebar.error(f"⚠️ Falha ao ler {nome_camada}.")
            continue
            
        col_classe = next((col for col in gdf.columns if col.upper() in ["CLASSE", "VULNERABILIDADE", "NOME", "TIPO"]), None)
        if not col_classe and len(gdf.columns) > 1:
            col_classe = [col for col in gdf.columns if col != 'geometry'][0]

        # MÓDULO DE ESTATÍSTICA ZONAL (Cálculo de Área)
        if col_classe and ("Vulnerabilidade" in nome_camada or "Uso" in nome_camada or "Geologia" in nome_camada):
            st.sidebar.markdown("---")
            st.sidebar.subheader(f"📊 Área: {nome_camada}")
            
            gdf_calc = gdf.to_crs(epsg=31984)
            gdf_calc['Area_km2'] = gdf_calc.geometry.area / 10**6
            resumo = gdf_calc.groupby(col_classe)['Area_km2'].sum().reset_index()
            resumo['%'] = (resumo['Area_km2'] / resumo['Area_km2'].sum()) * 100
            
            resumo['Area_km2'] = resumo['Area_km2'].round(2)
            resumo['%'] = resumo['%'].round(2)
            resumo.rename(columns={col_classe: 'Classe'}, inplace=True)
            
            st.sidebar.dataframe(resumo, hide_index=True, use_container_width=True)

        if gdf.crs is not None and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        fg = folium.FeatureGroup(name=nome_camada)

        def definir_estilo(feature, camada=nome_camada, coluna=col_classe, cor_idx=idx):
            valor = str(feature['properties'].get(coluna, '')).strip()
            if "Vulnerabilidade" in camada:
                cor = cores_vulnerabilidade.get(valor, '#969696')
                return {'fillColor': cor, 'color': '#000000', 'weight': 0.5, 'fillOpacity': 0.8}
            cor_generica = paleta_generica[cor_idx % len(paleta_generica)]
            return {'fillColor': cor_generica, 'color': cor_generica, 'weight': 1, 'fillOpacity': 0.5}

        folium.GeoJson(
            gdf,
            name=nome_camada,
            style_function=definir_estilo,
            tooltip=folium.GeoJsonTooltip(fields=[col_classe], aliases=["Classe: "]) if col_classe else None
        ).add_to(fg)

        fg.add_to(m)

# 9. Controles e Renderização
folium.LayerControl(collapsed=False).add_to(m)
st_folium(m, width=1000, height=600)
