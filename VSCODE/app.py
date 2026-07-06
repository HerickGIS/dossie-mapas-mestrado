import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from pathlib import Path
import pandas as pd

# =====================================================================
# 1. CONFIGURAÇÃO E ESTADO DA SESSÃO
# =====================================================================
st.set_page_config(page_title="Dashboard BHRC", layout="wide", initial_sidebar_state="expanded")

if "gdf_processado" not in st.session_state:
    st.session_state["gdf_processado"] = None
if "coluna_analise" not in st.session_state:
    st.session_state["coluna_analise"] = None

st.title("💧 Sistema de Inteligência Geográfica: Bacia do Rio do Carmo")
st.markdown("**Análise Espacial, Ecodinâmica e Geoprocessamento Dinâmico**")

# =====================================================================
# 2. RADAR DE ARQUIVOS (Busca todos os .geojson na pasta)
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent if BASE_DIR.name == "VSCODE" else BASE_DIR

todos_arquivos = [f for f in REPO_DIR.rglob("*") if f.suffix.lower() == '.geojson']

if not todos_arquivos:
    st.error("⚠️ Nenhum arquivo '.geojson' encontrado na pasta data!")
    st.stop()

mapas_encontrados = {}
for arquivo in sorted(todos_arquivos):
    nome_legivel = arquivo.stem.replace("dados_ppgeo_bh_", "").replace("dados_", "").replace("_", " ").title()
    nome_legivel = nome_legivel.replace("Ana", "ANA").replace("Map Biomas", "MapBiomas").replace("Ibge", "IBGE")
    mapas_encontrados[nome_legivel] = arquivo

@st.cache_data(show_spinner=False)
def carregar_mapa(caminho): 
    return gpd.read_file(caminho)

def extrair_colunas_validas(gdf):
    return [col for col in gdf.columns if col.lower() not in ['geometry', 'id', 'fid', 'objectid', 'shape_area', 'shape_length']]

# =====================================================================
# 3. MOTOR UNIVERSAL DE CORES (Sincroniza Mapa e Gráfico)
# =====================================================================
cores_vulnerabilidade = {
    'MUITO BAIXA': '#1a9850', 'BAIXA': '#91cf60', 'MÉDIA': '#fee08b', 'MEDIA': '#fee08b',
    'ALTA': '#fc8d59', 'MUITO ALTA': '#d73027', 'SEM CLASSIFICAÇÃO': '#969696', 'SEM CLASSIFICACAO': '#969696'
}

def gerar_paleta(valores, nome_camada):
    valores_unicos = sorted(list(set(valores)))
    
    # Se a camada envolver vulnerabilidade, força as cores oficiais
    if "vulnerabilidade" in nome_camada.lower():
        return {str(v): cores_vulnerabilidade.get(str(v).strip().upper(), '#808080') for v in valores_unicos}
    
    # Se for qualquer outro dado, cria uma paleta automática usando o Plotly
    paleta_plotly = px.colors.qualitative.Plotly + px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    paleta_sincronizada = {}
    for i, v in enumerate(valores_unicos):
        paleta_sincronizada[str(v)] = paleta_plotly[i % len(paleta_plotly)]
    return paleta_sincronizada

# =====================================================================
# 4. PAINEL LATERAL (CONTROLE GERAL E GEOPROCESSAMENTO)
# =====================================================================
st.sidebar.header("⚙️ Configurações da Análise")
modo_analise = st.sidebar.radio("Escolha o Modo de Geoprocessamento:", ["1. Visão Geral (Bacia Inteira)", "2. Micro-Análise (Recorte Espacial)"])
st.sidebar.markdown("---")

gdf_atual = None
coluna_atual = None
nome_analise = ""

if modo_analise == "1. Visão Geral (Bacia Inteira)":
    st.sidebar.subheader("🗺️ Camada Principal")
    camada_alvo = st.sidebar.selectbox("Selecione a Camada de Estudo:", list(mapas_encontrados.keys()))
    
    if camada_alvo:
        gdf_bruto = carregar_mapa(str(mapas_encontrados[camada_alvo]))
        colunas_alvo = extrair_colunas_validas(gdf_bruto)
        col_selecionada = st.sidebar.selectbox("Qual coluna deseja analisar/colorir?", colunas_alvo)
        
        if st.sidebar.button("🚀 Carregar Análise", type="primary"):
            gdf_bruto = gdf_bruto.to_crs(epsg=31984)
            gdf_bruto['Area_km2'] = gdf_bruto.geometry.area / 10**6
            st.session_state["gdf_processado"] = gdf_bruto
            st.session_state["coluna_analise"] = col_selecionada
            st.session_state["nome_camada_ativa"] = camada_alvo

elif modo_analise == "2. Micro-Análise (Recorte Espacial)":
    st.sidebar.subheader("🎯 1. Camada de Estudo")
    camada_alvo = st.sidebar.selectbox("O que será analisado?", list(mapas_encontrados.keys()), index=0)
    gdf_alvo_bruto = carregar_mapa(str(mapas_encontrados[camada_alvo]))
    col_alvo_selecionada = st.sidebar.selectbox("Coluna do Alvo para gerar os gráficos:", extrair_colunas_validas(gdf_alvo_bruto))
    
    st.sidebar.subheader("✂️ 2. Máscara de Recorte (Faca)")
    camada_mascara = st.sidebar.selectbox("Qual camada fará o corte?", list(mapas_encontrados.keys()), index=1)
    gdf_mask_bruto = carregar_mapa(str(mapas_encontrados[camada_mascara]))
    col_mask_selecionada = st.sidebar.selectbox("Coluna para buscar o polígono de corte:", extrair_colunas_validas(gdf_mask_bruto))
    
    valores_recorte = sorted(gdf_mask_bruto[col_mask_selecionada].astype(str).unique())
    valor_faca = st.sidebar.selectbox(f"Selecione o limite exato de {col_mask_selecionada}:", valores_recorte)

    if st.sidebar.button("✂️ Executar Recorte e Recalcular", type="primary"):
        with st.spinner("Realizando Intersecção Espacial..."):
            try:
                # Prepara projeções para o corte
                gdf_a = gdf_alvo_bruto.to_crs(epsg=31984)[[col_alvo_selecionada, 'geometry']]
                gdf_m = gdf_mask_bruto.to_crs(epsg=31984)
                
                # Filtra a faca exata (Ex: MOSSORÓ)
                mascara_filtrada = gdf_m[gdf_m[col_mask_selecionada].astype(str) == str(valor_faca)][['geometry']]
                
                # Faz o geoprocessamento (Clip)
                gdf_cortado = gpd.overlay(gdf_a, mascara_filtrada, how="intersection")
                
                if gdf_cortado.empty:
                    st.sidebar.error("Sem intersecção física nestas áreas.")
                else:
                    gdf_cortado['Area_km2'] = gdf_cortado.geometry.area / 10**6
                    st.session_state["gdf_processado"] = gdf_cortado
                    st.session_state["coluna_analise"] = col_alvo_selecionada
                    st.session_state["nome_camada_ativa"] = camada_alvo
            except Exception as e:
                st.sidebar.error(f"Erro no geoprocessamento: {e}")

# =====================================================================
# 5. RENDERIZAÇÃO DA INTERFACE UNIFICADA (MAPA + GRÁFICOS)
# =====================================================================
if st.session_state["gdf_processado"] is not None:
    gdf_trabalho = st.session_state["gdf_processado"].copy()
    coluna_foco = st.session_state["coluna_analise"]
    camada_nome = st.session_state["nome_camada_ativa"]
    
    gdf_trabalho[coluna_foco] = gdf_trabalho[coluna_foco].astype(str).str.upper().str.strip()

    st.markdown("---")
    
    # ---------------- INTERATIVIDADE E FILTROS ----------------
    controle_col1, controle_col2 = st.columns([1, 1])
    with controle_col1:
        tipo_grafico = st.selectbox("📊 Tipo de Gráfico Visual:", ["Gráfico de Rosca (Donut)", "Gráfico de Pizza", "Gráfico de Barras"])
    with controle_col2:
        categorias_existentes = sorted(gdf_trabalho[coluna_foco].unique())
        # Filtro reverso! Se o usuário preencher, o mapa e o gráfico cortam para mostrar só o que ele pediu
        filtro_usuario = st.multiselect(
            "🔍 Deseja Filtrar Resultados? (Deixe vazio para ver tudo)", 
            options=categorias_existentes,
            help="Selecione itens aqui para isolá-los no mapa e no gráfico simultaneamente."
        )
    
    # Aplica o filtro interativo (O usuário respondeu "Deseja Filtrar?" = Sim)
    if filtro_usuario:
        gdf_trabalho = gdf_trabalho[gdf_trabalho[coluna_foco].isin(filtro_usuario)]
    
    # Gera a Paleta Sincronizada baseada no que sobrou
    paleta_mestra = gerar_paleta(gdf_trabalho[coluna_foco], camada_nome)

    # Prepara os dados para o Gráfico
    resumo_df = gdf_trabalho.groupby(coluna_foco)['Area_km2'].sum().reset_index()
    resumo_df['%'] = (resumo_df['Area_km2'] / resumo_df['Area_km2'].sum()) * 100
    resumo_df['Rotulo'] = resumo_df['Area_km2'].round(2).astype(str) + " km²"

    col_mapa_main, col_grafico_main = st.columns([6, 4])
    
    # ---------------- O GRÁFICO (PLOTLY) ----------------
    with col_grafico_main:
        if tipo_grafico == "Gráfico de Rosca (Donut)":
            fig = px.pie(resumo_df, values='Area_km2', names=coluna_foco, hole=0.4, color=coluna_foco, color_discrete_map=paleta_mestra)
            fig.update_traces(textposition='inside', textinfo='percent+label')
        elif tipo_grafico == "Gráfico de Pizza":
            fig = px.pie(resumo_df, values='Area_km2', names=coluna_foco, color=coluna_foco, color_discrete_map=paleta_mestra)
            fig.update_traces(textposition='inside', textinfo='percent+label')
        else:
            fig = px.bar(resumo_df, x='Area_km2', y=coluna_foco, color=coluna_foco, color_discrete_map=paleta_mestra, text='Rotulo', orientation='h')
            fig.update_traces(textposition='outside')
            fig.update_layout(showlegend=False, xaxis_title="Área Espacial (km²)", yaxis_title="")
        
        fig.update_layout(title=f"Distribuição Geográfica: {camada_nome}", margin=dict(t=50, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("Consultar Tabela (Dados Recalculados)"):
            st.dataframe(resumo_df.rename(columns={coluna_foco: 'Atributo', 'Area_km2': 'Área FÍSICA (km²)', '%': 'Porcentagem (%)'}).drop(columns=['Rotulo']), hide_index=True)

    # ---------------- O MAPA (FOLIUM) ----------------
    with col_mapa_main:
        gdf_wgs84 = gdf_trabalho.to_crs(epsg=4326)
        
        # Centraliza o mapa inteligentemente com base na análise atual
        centro_y = gdf_wgs84.geometry.centroid.y.mean()
        centro_x = gdf_wgs84.geometry.centroid.x.mean()
        zoom = 10 if modo_analise == "2. Micro-Análise (Recorte Espacial)" else 9
        
        m_principal = folium.Map(location=[centro_y, centro_x], zoom_start=zoom, tiles=None)
        folium.TileLayer('CartoDB positron', name='Mapa Base (Claro)', control=True).add_to(m_principal)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite (Esri)', overlay=False, control=True).add_to(m_principal)

        def estilo_sincronizado(feature):
            valor_atributo = str(feature['properties'].get(coluna_foco, '')).strip().upper()
            cor = paleta_mestra.get(valor_atributo, '#000000') # Puxa exatamente a mesma cor do gráfico
            return {'fillColor': cor, 'color': '#222222', 'weight': 1, 'fillOpacity': 0.85}

        folium.GeoJson(
            gdf_wgs84,
            name=camada_nome,
            style_function=estilo_sincronizado,
            tooltip=folium.GeoJsonTooltip(fields=[coluna_foco], aliases=[f"{coluna_foco}: "]),
            highlight_function=lambda x: {'weight': 3, 'color': 'white', 'fillOpacity': 1}
        ).add_to(m_principal)
        
        folium.LayerControl(collapsed=False).add_to(m_principal)
        
        # O parâmetro return_on_hover=False garante que o mapa não fique recarregando sozinho
        st_folium(m_principal, use_container_width=True, height=500, return_on_hover=False)

else:
    st.info("👈 Utilize o Painel Lateral para selecionar os mapas, as colunas e carregar a sua análise.")
