import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from pathlib import Path

# 1. Configuração inicial da página
st.set_page_config(page_title="Dashboard BHRC", layout="wide", initial_sidebar_state="expanded")

st.title("💧 Dashboard Analítico: Bacia Hidrográfica do Rio do Carmo")
st.markdown("**Sistema de Apoio à Decisão: Ecodinâmica e Impacto Socioespacial**")

# =====================================================================
# 2. MÓDULO DE FUNDAMENTAÇÃO METODOLÓGICA
# =====================================================================
with st.expander("📖 Metodologia e Modelagem Espacial (Jean Tricart)", expanded=False):
    st.markdown("""
    A análise de vulnerabilidade desta bacia baseia-se nos princípios da **Ecodinâmica de Tricart (1977)**, integrando a dimensão do meio físico e a pressão antrópica.
    """)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Vulnerabilidade Natural (VN)")
        st.latex(r"VN = \frac{\text{Geomorfo} + \text{Geologia} + \text{Pedologia} + \text{Vegetação} + \text{Uso e Cobertura}}{5}")
    with col2:
        st.subheader("Vulnerabilidade Ambiental (VA)")
        st.latex(r"VA = 0.2[\text{Geomorfo}] + 0.1[\text{Geologia}] + 0.1[\text{Pedologia}] + 0.1[\text{Vegetação}] + 0.5[\text{Uso e Cobertura}]")

# 3. O RADAR AUTOMÁTICO DE ARQUIVOS
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent if BASE_DIR.name == "VSCODE" else BASE_DIR

todos_arquivos = [f for f in REPO_DIR.rglob("*") if f.suffix.lower() == '.geojson']

if not todos_arquivos:
    st.error("⚠️ Nenhum arquivo '.geojson' encontrado no repositório!")
    st.stop()

mapas_encontrados = {}
for arquivo in sorted(todos_arquivos):
    nome_legivel = arquivo.stem.replace("dados_ppgeo_bh_", "").replace("dados_", "").replace("_", " ").title()
    nome_legivel = nome_legivel.replace("Ana", "ANA").replace("Map Biomas", "MapBiomas").replace("Ibge", "IBGE")
    mapas_encontrados[nome_legivel] = arquivo

# 4. COLUNAS DE ATRIBUTOS (MAPEAMENTO EXATO)
colunas_principais = {
    "Vulnerabilidade Natural": "CLASSE",
    "Vulnerabilidade Ambiental": "CLASSE",
    "Geologia": "NOME_UNIDA",
    "Geomorfologia": "nm_unidade",
    "Tipos De Solos (Pedologia)": "LEG_SINOT",
    "Vegetacao": "CLASSE",
    "Municipios": "NM_MUN",
    "Drenagem ANA": "nooriginal",
    "Rio Carmo Curso": "nooriginal",
    "Bacia Delimitacao": "nome_bacia",
    "IBGE Cruzamento Carmo": "CLASSE" # O arquivo do IBGE herdou a coluna da Ecodinâmica no cruzamento!
}

# 5. DICIONÁRIOS DE CORES
cores_vulnerabilidade = {
    'MUITO BAIXA': '#1a9850', 'BAIXA': '#91cf60', 'MÉDIA': '#fee08b', 'MEDIA': '#fee08b',
    'ALTA': '#fc8d59', 'MUITO ALTA': '#d73027', 'SEM CLASSIFICAÇÃO': '#969696', 'SEM CLASSIFICACAO': '#969696'
}
paleta_generica = ['#377eb8', '#984ea3', '#ff7f00', '#a65628', '#f781bf']

@st.cache_data(show_spinner=False)
def carregar_mapa(caminho_arquivo: str): 
    return gpd.read_file(caminho_arquivo)

# 6. BARRA LATERAL E SLICERS
st.sidebar.header("⚙️ Painel de Controle")
camadas_selecionadas = st.sidebar.multiselect(
    "1. Ligue e desligue as variáveis no mapa:", 
    list(mapas_encontrados.keys()),
    default=["Vulnerabilidade Natural"] if "Vulnerabilidade Natural" in mapas_encontrados else [list(mapas_encontrados.keys())[0]]
)

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
            
        col_classe = colunas_principais.get(nome_camada)
        if not col_classe:
            col_classe = next((col for col in gdf.columns if col.upper() in ["CLASSE", "VULNERABILIDADE", "NOME", "TIPO"]), None)
            if not col_classe and len(gdf.columns) > 1:
                col_classe = [col for col in gdf.columns if col != 'geometry'][0]

        if col_classe and col_classe in gdf.columns:
            gdf[col_classe] = gdf[col_classe].astype(str).str.upper()
            classes_disponiveis = sorted(gdf[col_classe].unique())
            
            classes_filtradas = st.sidebar.multiselect(
                f"Filtrar {nome_camada}:",
                options=classes_disponiveis,
                default=classes_disponiveis 
            )
            gdf = gdf[gdf[col_classe].isin(classes_filtradas)]

        dados_para_mapa[nome_camada] = {"gdf": gdf, "col_classe": col_classe}

        # LÓGICA ESPACIAL E SÓCIO-DEMOGRÁFICA
        if col_classe and col_classe in gdf.columns and not gdf.empty:
            # 1. Análise de Área (Padrão)
            if "Vulnerabilidade" in nome_camada or "Uso" in nome_camada or "Geologia" in nome_camada:
                gdf_calc = gdf.to_crs(epsg=31984) 
                gdf_calc['Area_km2'] = gdf_calc.geometry.area / 10**6
                resumo = gdf_calc.groupby(col_classe)['Area_km2'].sum().reset_index()
                resumo['%'] = (resumo['Area_km2'] / resumo['Area_km2'].sum()) * 100
                resumo['Area_km2'] = resumo['Area_km2'].round(2)
                resumo['%'] = resumo['%'].round(2)
                resumo['Rotulo_Grafico'] = resumo['Area_km2'].astype(str) + " km² (" + resumo['%'].astype(str) + "%)"
                dados_para_graficos[nome_camada] = {"tipo": "area", "df": resumo, "coluna": col_classe}
            
            # 2. Análise Demográfica (IBGE)
            elif "IBGE" in nome_camada.upper():
                # Tenta achar a coluna de população (o geobr usa 'pop_total', 'v0001', etc)
                col_pop = next((c for c in gdf.columns if 'pop' in c.lower() or c == 'v0001'), None)
                if col_pop:
                    # Força a conversão para numérico, ignorando erros (caso venham textos)
                    gdf[col_pop] = pd.to_numeric(gdf[col_pop], errors='coerce').fillna(0)
                    resumo_pop = gdf.groupby(col_classe)[col_pop].sum().reset_index()
                    resumo_pop.rename(columns={col_pop: 'Populacao'}, inplace=True)
                    resumo_pop['%'] = (resumo_pop['Populacao'] / resumo_pop['Populacao'].sum()) * 100
                    resumo_pop['%'] = resumo_pop['%'].round(2)
                    resumo_pop['Rotulo_Grafico'] = resumo_pop['Populacao'].astype(int).astype(str) + " hab. (" + resumo_pop['%'].astype(str) + "%)"
                    dados_para_graficos[nome_camada] = {"tipo": "populacao", "df": resumo_pop, "coluna": col_classe}

# =====================================================================
# 7. DIVISÃO DA TELA: MAPA (Esquerda) e DADOS (Direita)
# =====================================================================
col_mapa, col_dados = st.columns([6, 4])

with col_mapa:
    st.subheader("Visualizador Cartográfico")
    
    # SETUP AVANÇADO DE BASEMAPS (Esri, TopoMap e CartoDB)
    m = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles=None)
    
    folium.TileLayer('CartoDB positron', name='Mapa Base (Claro)', control=True).add_to(m)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satélite (Esri World Imagery)',
        overlay=False,
        control=True
    ).add_to(m)
    folium.TileLayer(
        tiles='https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
        attr='Map data: © OpenStreetMap contributors, SRTM | Map style: © OpenTopoMap',
        name='Topografia e Hidrografia',
        overlay=False,
        control=True
    ).add_to(m)
    
    for idx, (nome_camada, info) in enumerate(dados_para_mapa.items()):
        gdf = info["gdf"]
        col_classe = info["col_classe"]
        
        if gdf.empty:
            continue 
            
        if gdf.crs is not None and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")

        fg = folium.FeatureGroup(name=nome_camada)

        def definir_estilo(feature, camada=nome_camada, coluna=col_classe, cor_idx=idx):
            if coluna and coluna in feature['properties']:
                valor = str(feature['properties'].get(coluna, '')).strip().upper()
                if "Vulnerabilidade" in camada or "IBGE" in camada.upper():
                    cor = cores_vulnerabilidade.get(valor, '#969696')
                    peso = 0.8 if "IBGE" in camada.upper() else 0.5
                    return {'fillColor': cor, 'color': '#000000', 'weight': peso, 'fillOpacity': 0.7}
            cor_generica = paleta_generica[cor_idx % len(paleta_generica)]
            return {'fillColor': cor_generica, 'color': '#333333', 'weight': 0.5, 'fillOpacity': 0.5}

        # Verificação extra de segurança para o Tooltip
        mostrar_tooltip = None
        if col_classe and col_classe in gdf.columns:
            mostrar_tooltip = folium.GeoJsonTooltip(fields=[col_classe], aliases=["Atributo: "])

        folium.GeoJson(
            gdf,
            name=nome_camada,
            style_function=definir_estilo,
            highlight_function=lambda x: {'weight': 2, 'color': 'black', 'fillOpacity': 0.9},
            tooltip=mostrar_tooltip
        ).add_to(fg)

        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    mapa_interativo = st_folium(m, use_container_width=True, height=600, return_on_hover=False)

# =====================================================================
# 8. PAINEL DE INTELIGÊNCIA SÓCIO-ESPACIAL
# =====================================================================
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
    
    if dados_para_graficos:
        for nome_camada, info in dados_para_graficos.items():
            df_plot = info["df"]
            coluna_ref = info["coluna"]
            tipo_grafico = info["tipo"]
            
            if tipo_grafico == "area":
                fig = px.bar(
                    df_plot, x='Area_km2', y=coluna_ref, orientation='h',
                    title=f"📊 Área por Categoria: {nome_camada}",
                    color=coluna_ref, color_discrete_map=cores_vulnerabilidade,
                    text='Rotulo_Grafico', custom_data=['%']
                )
                eixo_x_titulo = "Área (km²)"
            else:
                fig = px.bar(
                    df_plot, x='Populacao', y=coluna_ref, orientation='h',
                    title=f"👥 População Exposta por Vulnerabilidade",
                    color=coluna_ref, color_discrete_map=cores_vulnerabilidade,
                    text='Rotulo_Grafico', custom_data=['%']
                )
                eixo_x_titulo = "População (Habitantes)"
            
            fig.update_traces(textposition='outside')
            fig.update_layout(
                showlegend=False, xaxis_title=eixo_x_titulo, yaxis_title="", 
                yaxis={'categoryorder':'total ascending'}, margin=dict(r=150) 
            )
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander(f"Consultar Tabela: {nome_camada}"):
                st.dataframe(df_plot.drop(columns=['Rotulo_Grafico']), hide_index=True, use_container_width=True)
