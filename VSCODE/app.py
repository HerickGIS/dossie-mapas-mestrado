import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from pathlib import Path

# 1. Configuração inicial da página
st.set_page_config(page_title="Dashboard BHRC", layout="wide", initial_sidebar_state="expanded")

st.title("💧 Dashboard Analítico: Bacia Hidrográfica do Rio do Carmo")
st.markdown("**Sistema de Apoio à Decisão e Ecodinâmica**")

# =====================================================================
# 2. MÓDULO DE FUNDAMENTAÇÃO METODOLÓGICA
# =====================================================================
with st.expander("📖 Metodologia e Modelagem Espacial (Jean Tricart)", expanded=False):
    st.markdown("""
    A análise de vulnerabilidade desta bacia baseia-se nos princípios da **Ecodinâmica de Tricart (1977)**, que avalia a relação entre os processos de pedogênese (formação do solo) e morfogênese (degradação).
    
    A modelagem em Sistema de Informação Geográfica (SIG) foi realizada por meio de Álgebra de Mapas, integrando cinco variáveis biofísicas: **Geomorfologia, Geologia, Pedologia, Vegetação e Uso e Cobertura da Terra**.
    """)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Vulnerabilidade Natural (VN)")
        st.markdown("Avalia a suscetibilidade intrínseca do meio físico, calculada pela média aritmética dos pesos atribuídos às classes.")
        st.latex(r"VN = \frac{Geomorfologia + Geologia + Pedologia + Vegetação + Uso e Cobertura da Terra}{5}")
    with col2:
        st.subheader("Vulnerabilidade Ambiental (VA)")
        st.markdown("Insere o peso da pressão antrópica. O fator 'Uso e Cobertura da Terra' recebe o peso dominante (0.5).")
        st.latex(r"VA = 0.2 x [Geomorfologia] + 0.1 x [Geologia] + 0.1 x [Pedologia] + 0.1 x [Vegetação] + 0.5 x [Uso e Cobertura da Terra]")

# 3. O RADAR AUTOMÁTICO DE ARQUIVOS
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent if BASE_DIR.name == "VSCODE" else BASE_DIR

todos_arquivos = [f for f in REPO_DIR.rglob("*") if f.suffix.lower() == '.geojson']

if not todos_arquivos:
    st.error("⚠️ Nenhum arquivo '.geojson' encontrado no repositório!")
    st.stop()

mapas_encontrados = {}
for arquivo in sorted(todos_arquivos):
    nome_legivel = arquivo.stem.replace("dados_ppgeo_bh_", "").replace("_", " ").title()
    nome_legivel = nome_legivel.replace("Ana", "ANA").replace("Map Biomas", "MapBiomas")
    mapas_encontrados[nome_legivel] = arquivo

# 4. DICIONÁRIOS DE CORES
cores_vulnerabilidade = {
    'MUITO BAIXA': '#1a9850', 'BAIXA': '#91cf60', 'MÉDIA': '#fee08b', 'MEDIA': '#fee08b',
    'ALTA': '#fc8d59', 'MUITO ALTA': '#d73027', 'SEM CLASSIFICAÇÃO': '#969696', 'SEM CLASSIFICACAO': '#969696'
}
paleta_generica = ['#377eb8', '#984ea3', '#ff7f00', '#a65628', '#f781bf']

@st.cache_data(show_spinner=False)
def carregar_mapa(caminho_arquivo: str): 
    return gpd.read_file(caminho_arquivo)

# =====================================================================
# 5. BARRA LATERAL (CONTROLE E SLICERS ESTILO POWER BI)
# =====================================================================
st.sidebar.header("⚙️ Painel de Controle")
camadas_selecionadas = st.sidebar.multiselect(
    "1. Ligue e desligue as variáveis no mapa:", 
    list(mapas_encontrados.keys()),
    default=["Vulnerabilidade Natural"] if "Vulnerabilidade Natural" in mapas_encontrados else [list(mapas_encontrados.keys())[0]]
)

# Dicionários para guardar os dados filtrados que vão renderizar o mapa e os gráficos
dados_para_mapa = {}
dados_para_graficos = {}

if camadas_selecionadas:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🎯 Filtros Interativos (Slicers)")
    
    for nome_camada in camadas_selecionadas:
        caminho_do_mapa = mapas_encontrados[nome_camada]
        try:
            gdf = carregar_mapa(str(caminho_do_mapa))
        except Exception:
            st.sidebar.error(f"⚠️ Falha ao ler {nome_camada}.")
            continue
            
        col_classe = next((col for col in gdf.columns if col.upper() in ["CLASSE", "VULNERABILIDADE", "NOME", "TIPO"]), None)
        if not col_classe and len(gdf.columns) > 1:
            col_classe = [col for col in gdf.columns if col != 'geometry'][0]

        # SE EXISTIR CLASSE, CRIA O FILTRO DINÂMICO!
        if col_classe:
            # Transforma tudo em maiúsculo para padronizar
            gdf[col_classe] = gdf[col_classe].astype(str).str.upper()
            
            # Pega todas as classes únicas disponíveis nesta camada
            classes_disponiveis = sorted(gdf[col_classe].unique())
            
            # Cria o Slicer no menu lateral
            classes_filtradas = st.sidebar.multiselect(
                f"Filtrar {nome_camada}:",
                options=classes_disponiveis,
                default=classes_disponiveis # Vem tudo selecionado por padrão
            )
            
            # APLICA O FILTRO NO DATAFRAME ANTES DE IR PARA O MAPA
            gdf = gdf[gdf[col_classe].isin(classes_filtradas)]

        # Salva o GDF já filtrado para desenhar o mapa depois
        dados_para_mapa[nome_camada] = {"gdf": gdf, "col_classe": col_classe}

        # Processamento de Área para os Gráficos (Apenas se sobrou algum dado após o filtro)
        if col_classe and not gdf.empty and ("Vulnerabilidade" in nome_camada or "Uso" in nome_camada or "Geologia" in nome_camada):
            gdf_calc = gdf.to_crs(epsg=31984) # SIRGAS 2000 UTM 24S
            gdf_calc['Area_km2'] = gdf_calc.geometry.area / 10**6
            resumo = gdf_calc.groupby(col_classe)['Area_km2'].sum().reset_index()
            resumo['%'] = (resumo['Area_km2'] / resumo['Area_km2'].sum()) * 100
            dados_para_graficos[nome_camada] = {"df": resumo, "coluna": col_classe}

# =====================================================================
# 6. DIVISÃO DA TELA: MAPA (Esquerda) e PAINEL DE DADOS (Direita)
# =====================================================================
col_mapa, col_dados = st.columns([6, 4])

with col_mapa:
    st.subheader("Visualizador Cartográfico")
    m = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles="CartoDB positron")
    
    # Desenha as camadas filtradas no mapa
    for idx, (nome_camada, info) in enumerate(dados_para_mapa.items()):
        gdf = info["gdf"]
        col_classe = info["col_classe"]
        
        if gdf.empty:
            continue # Pula a camada se o usuário tirou todas as opções no filtro
            
        if gdf.crs is not None and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        fg = folium.FeatureGroup(name=nome_camada)

        def definir_estilo(feature, camada=nome_camada, coluna=col_classe, cor_idx=idx):
            valor = str(feature['properties'].get(coluna, '')).strip().upper()
            if "Vulnerabilidade" in camada:
                cor = cores_vulnerabilidade.get(valor, '#969696')
                return {'fillColor': cor, 'color': '#333333', 'weight': 0.5, 'fillOpacity': 0.8}
            cor_generica = paleta_generica[cor_idx % len(paleta_generica)]
            return {'fillColor': cor_generica, 'color': '#333333', 'weight': 0.5, 'fillOpacity': 0.5}

        folium.GeoJson(
            gdf,
            name=nome_camada,
            style_function=definir_estilo,
            highlight_function=lambda x: {'weight': 2, 'color': 'black', 'fillOpacity': 0.9},
            tooltip=folium.GeoJsonTooltip(fields=[col_classe], aliases=["Classe: "]) if col_classe else None
        ).add_to(fg)

        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    mapa_interativo = st_folium(m, use_container_width=True, height=600, return_on_hover=False)

with col_dados:
    st.subheader("Painel de Inteligência")
    
    clique = mapa_interativo.get("last_active_drawing")
    if clique:
        st.info("📍 **Atributos da Área Clicada:**")
        prop_limpas = {k: v for k, v in clique.get("properties", {}).items() if k not in ['style', 'highlight']}
        st.json(prop_limpas)
    else:
        st.markdown("*Clique em qualquer polígono no mapa para focar em seus atributos.*")
    
    st.markdown("---")
    
    # 7. GRÁFICOS INTERATIVOS SINCRONIZADOS
    if dados_para_graficos:
        for nome_camada, info in dados_para_graficos.items():
            df_plot = info["df"]
            coluna_ref = info["coluna"]
            
            # Gráfico de barras horizontais (ótimo para comparar as áreas filtradas)
            fig = px.bar(
                df_plot, 
                x='Area_km2', 
                y=coluna_ref, 
                orientation='h',
                title=f"📊 Área por Classe: {nome_camada} (km²)",
                color=coluna_ref,
                color_discrete_map=cores_vulnerabilidade,
                text_auto='.2f'
            )
            fig.update_layout(showlegend=False, xaxis_title="Área (km²)", yaxis_title="Classes", yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
