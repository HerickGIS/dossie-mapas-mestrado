import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from pathlib import Path
import pandas as pd

# 1. Configuração inicial da página e Sessões de Memória
st.set_page_config(page_title="Dashboard BHRC", layout="wide", initial_sidebar_state="expanded")

if "gdf_microanalise" not in st.session_state:
    st.session_state["gdf_microanalise"] = None
if "info_microanalise" not in st.session_state:
    st.session_state["info_microanalise"] = None

st.title("💧 Dashboard Analítico: Bacia Hidrográfica do Rio do Carmo")
st.markdown("**Sistema de Apoio à Decisão: Ecodinâmica e Impacto Socioespacial**")

# =====================================================================
# 2. O RADAR AUTOMÁTICO DE ARQUIVOS (Lê tudo na pasta data)
# =====================================================================
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

# =====================================================================
# 3. MOTORES DE CORES E COLUNAS PADRÃO
# =====================================================================
# Dicionário fixo apenas para a Ecodinâmica de Tricart (Dissertação)
cores_vulnerabilidade = {
    'MUITO BAIXA': '#1a9850', 'BAIXA': '#91cf60', 'MÉDIA': '#fee08b', 'MEDIA': '#fee08b',
    'ALTA': '#fc8d59', 'MUITO ALTA': '#d73027', 'SEM CLASSIFICAÇÃO': '#969696', 'SEM CLASSIFICACAO': '#969696'
}

def obter_coluna_real(gdf):
    """Encontra a coluna principal de qualquer shapefile/geojson automaticamente."""
    colunas_prioritarias = ["CLASSE", "NOME_UNIDA", "NM_UNIDADE", "LEG_SINOT", "NM_MUN", "NOORIGINAL", "NOME_BACIA"]
    # 1. Tenta achar uma coluna prioritária exata
    for col_pri in colunas_prioritarias:
        for col in gdf.columns:
            if col.upper() == col_pri:
                return col
    # 2. Fallback: Pega a primeira coluna de texto que não seja geometria ou ID
    colunas_validas = [col for col in gdf.columns if col.lower() not in ['geometry', 'id', 'fid', 'objectid', 'shape_area', 'shape_length']]
    for col in colunas_validas:
        if gdf[col].dtype == 'object':
            return col
    return colunas_validas[0] if colunas_validas else None

def gerar_paleta_dinamica(valores, is_vulnerabilidade=False):
    """Gera cores sincronizadas para mapas e gráficos."""
    valores_unicos = sorted(list(set(valores)))
    if is_vulnerabilidade:
        return {str(v): cores_vulnerabilidade.get(str(v).strip().upper(), '#808080') for v in valores_unicos}
    
    # Paleta Plotly automática para outras camadas (Geologia, Solos, IBGE)
    paleta_plotly = px.colors.qualitative.Pastel + px.colors.qualitative.Set3
    return {str(v): paleta_plotly[i % len(paleta_plotly)] for i, v in enumerate(valores_unicos)}

@st.cache_data(show_spinner=False)
def carregar_mapa_fisico(caminho_arquivo: str): 
    return gpd.read_file(caminho_arquivo)

# =====================================================================
# 4. INTERFACE: ABAS DO DASHBOARD
# =====================================================================
aba_mapa, aba_laboratorio = st.tabs([
    "🗺️ Visualizador Principal", 
    "🔬 Laboratório de Geoprocessamento (Clip & Join)"
])

# ---------------------------------------------------------------------
# ABA 1: VISUALIZADOR CARTOGRÁFICO
# ---------------------------------------------------------------------
with aba_mapa:
    st.sidebar.header("⚙️ Painel de Controle")
    camadas_selecionadas = st.sidebar.multiselect(
        "Ligue as variáveis no mapa:", list(mapas_encontrados.keys()),
        default=["Vulnerabilidade Natural"] if "Vulnerabilidade Natural" in mapas_encontrados else [list(mapas_encontrados.keys())[0]]
    )

    dados_para_mapa = {}
    
    if camadas_selecionadas:
        st.sidebar.markdown("---")
        st.sidebar.subheader("🎯 Filtros Interativos")
        for nome_camada in camadas_selecionadas:
            try:
                gdf = carregar_mapa_fisico(str(mapas_encontrados[nome_camada])).copy()
            except: continue
                
            col_padrao = obter_coluna_real(gdf)

            if col_padrao and col_padrao in gdf.columns:
                gdf[col_padrao] = gdf[col_padrao].astype(str).str.upper()
                classes_disponiveis = sorted(gdf[col_padrao].unique())
                classes_filtradas = st.sidebar.multiselect(f"Filtrar {nome_camada}:", options=classes_disponiveis, default=classes_disponiveis)
                gdf = gdf[gdf[col_padrao].isin(classes_filtradas)]
                dados_para_mapa[nome_camada] = {"gdf": gdf, "col_classe": col_padrao}

    col_mapa, col_dados = st.columns([6, 4])
    with col_mapa:
        m = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles=None)
        folium.TileLayer('CartoDB positron', name='Mapa Base (Claro)', control=True).add_to(m)
        folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satélite (Esri)', overlay=False, control=True).add_to(m)
        
        for idx, (nome_camada, info) in enumerate(dados_para_mapa.items()):
            gdf = info["gdf"]
            col_classe = info["col_classe"]
            if gdf.empty: continue 
            if gdf.crs is not None and gdf.crs != "EPSG:4326": gdf = gdf.to_crs("EPSG:4326")
            fg = folium.FeatureGroup(name=nome_camada)

            is_vuln = "Vulnerabilidade" in nome_camada
            paleta = gerar_paleta_dinamica(gdf[col_classe], is_vulnerabilidade=is_vuln)

            def definir_estilo(feature, camada=nome_camada, coluna=col_classe, p=paleta):
                valor = str(feature['properties'].get(coluna, '')).strip().upper()
                cor = p.get(valor, '#333333')
                peso_borda = 0.8 if "IBGE" in camada.upper() or "Municipios" in camada else 0.5
                return {'fillColor': cor, 'color': '#000000', 'weight': peso_borda, 'fillOpacity': 0.7}

            mostrar_tooltip = folium.GeoJsonTooltip(fields=[col_classe], aliases=[f"{col_classe}: "]) if col_classe and col_classe in gdf.columns else None
            folium.GeoJson(gdf, name=nome_camada, style_function=definir_estilo, highlight_function=lambda x: {'weight': 2, 'color': 'black', 'fillOpacity': 0.9}, tooltip=mostrar_tooltip).add_to(fg)
            fg.add_to(m)
            
        folium.LayerControl(collapsed=False).add_to(m)
        st_folium(m, use_container_width=True, height=600, return_on_hover=False)

    with col_dados:
        st.subheader("Painel de Inteligência")
        for nome_camada, info in dados_para_mapa.items():
            gdf_calc = info["gdf"].to_crs(epsg=31984)
            coluna = info["col_classe"]
            
            gdf_calc['Area_km2'] = gdf_calc.geometry.area / 10**6
            resumo = gdf_calc.groupby(coluna)['Area_km2'].sum().reset_index()
            resumo['%'] = (resumo['Area_km2'] / resumo['Area_km2'].sum()) * 100
            resumo['Rotulo'] = resumo['Area_km2'].round(2).astype(str) + " km² (" + resumo['%'].round(2).astype(str) + "%)"
            
            paleta = gerar_paleta_dinamica(resumo[coluna], is_vulnerabilidade="Vulnerabilidade" in nome_camada)
            
            fig = px.bar(resumo, x='Area_km2', y=coluna, orientation='h', title=f"📊 Área: {nome_camada}", color=coluna, color_discrete_map=paleta, text='Rotulo')
            fig.update_traces(textposition='outside')
            fig.update_layout(showlegend=False, xaxis_title="Área (km²)", yaxis_title="", yaxis={'categoryorder':'total ascending'}, margin=dict(r=150))
            st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------
# ABA 2: LABORATÓRIO DE GEOPROCESSAMENTO (CLIP + JOIN INTEGRADO)
# ---------------------------------------------------------------------
with aba_laboratorio:
    st.header("🔬 Recorte Espacial e Tabela Dinâmica")
    st.markdown("Use um polígono como máscara de recorte. O sistema cortará a geometria e unirá os atributos automaticamente (Intersect).")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. Camada de Estudo (Alvo)")
        camada_estudo = st.selectbox("O que será recortado? (Ex: Vulnerabilidade):", list(mapas_encontrados.keys()), index=0)
    
    with col2:
        st.subheader("2. Camada Máscara (Faca)")
        camada_mascara = st.selectbox("Quem fará o corte? (Ex: IBGE Setores ou Municípios):", list(mapas_encontrados.keys()), index=1)
        
        gdf_mask_bruto = carregar_mapa_fisico(str(mapas_encontrados[camada_mascara]))
        col_filtro = obter_coluna_real(gdf_mask_bruto)
        
        if col_filtro:
            valores_disponiveis = sorted(gdf_mask_bruto[col_filtro].astype(str).unique())
            valor_recorte = st.selectbox(f"Selecione o polígono de {col_filtro} para o recorte:", valores_disponiveis)
        else:
            st.error("Não foi possível identificar uma coluna válida para filtragem na máscara.")

    st.markdown("---")
    executar_lab = st.button("✂️ Executar Geoprocessamento (Clip & Join)", type="primary", use_container_width=True)

    if executar_lab and col_filtro:
        with st.spinner(f"Processando Álgebra de Mapas em {valor_recorte}..."):
            try:
                # 1. Prepara as projeções em UTM para cálculo de área perfeito
                gdf_alvo = carregar_mapa_fisico(str(mapas_encontrados[camada_estudo])).to_crs(epsg=31984)
                gdf_mask = carregar_mapa_fisico(str(mapas_encontrados[camada_mascara])).to_crs(epsg=31984)
                
                # 2. Limpa o alvo e encontra a coluna principal
                col_alvo_real = obter_coluna_real(gdf_alvo)
                if col_alvo_real: gdf_alvo = gdf_alvo[[col_alvo_real, 'geometry']]
                
                # 3. Isola a máscara e retém seus atributos para o Join!
                mascara_filtrada = gdf_mask[gdf_mask[col_filtro].astype(str) == valor_recorte]
                
                # 4. A MÁGICA: Overlay Intersection (Faz o Clip e o Join simultaneamente)
                gdf_recortado = gpd.overlay(gdf_alvo, mascara_filtrada, how="intersection")
                
                if gdf_recortado.empty:
                    st.warning(f"Sem intersecção física dentro de {valor_recorte}.")
                    st.session_state["gdf_microanalise"] = None
                else:
                    gdf_recortado['Area_Recorte_km2'] = gdf_recortado.geometry.area / 10**6
                    st.session_state["gdf_microanalise"] = gdf_recortado
                    st.session_state["info_microanalise"] = {
                        "valor_recorte": valor_recorte, 
                        "col_alvo": col_alvo_real,
                        "camada_estudo": camada_estudo
                    }
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

    # Renderiza os resultados se existirem na memória
    if st.session_state["gdf_microanalise"] is not None:
        gdf_recortado = st.session_state["gdf_microanalise"]
        info_sessao = st.session_state["info_microanalise"]
        col_alvo = info_sessao["col_alvo"]
        is_vuln_lab = "Vulnerabilidade" in info_sessao["camada_estudo"]

        st.success(f"✅ Análise em **{info_sessao['valor_recorte']}** concluída!")
        
        # Gera paleta sincronizada para o resultado
        paleta_lab = gerar_paleta_dinamica(gdf_recortado[col_alvo], is_vulnerabilidade=is_vuln_lab)
        
        col_result_mapa, col_result_grafico = st.columns([6, 4])
        
        with col_result_grafico:
            resumo_clip = gdf_recortado.groupby(col_alvo)['Area_Recorte_km2'].sum().reset_index()
            fig_clip = px.pie(resumo_clip, values='Area_Recorte_km2', names=col_alvo, title="Distribuição de Área", color=col_alvo, color_discrete_map=paleta_lab, hole=0.3)
            fig_clip.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_clip, use_container_width=True)
            
            with st.expander("Tabela de Atributos do Recorte (Join)"):
                st.dataframe(gdf_recortado.drop(columns=['geometry']), hide_index=True)

        with col_result_mapa:
            gdf_recortado_wgs = gdf_recortado.to_crs(epsg=4326)
            m_clip = folium.Map(location=[gdf_recortado_wgs.geometry.centroid.y.mean(), gdf_recortado_wgs.geometry.centroid.x.mean()], zoom_start=10, tiles="CartoDB positron")
            
            folium.GeoJson(
                gdf_recortado_wgs, 
                style_function=lambda x: {
                    'fillColor': paleta_lab.get(str(x['properties'].get(col_alvo, '')).strip().upper(), '#808080'), 
                    'color': 'black', 'weight': 1, 'fillOpacity': 0.8
                }, 
                tooltip=folium.GeoJsonTooltip(fields=[col_alvo, info_sessao["valor_recorte"]] if info_sessao["valor_recorte"] in gdf_recortado_wgs.columns else [col_alvo])
            ).add_to(m_clip)
            
            st_folium(m_clip, use_container_width=True, height=500, key="mapa_clip", return_on_hover=False)
