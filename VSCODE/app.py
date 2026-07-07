import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import HeatMap, Draw
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import pandas as pd
import io
import zipfile

# =====================================================================
# 1. CONFIGURAÇÃO E ESTADO DA SESSÃO
# =====================================================================
st.set_page_config(page_title="Dossiê BHRC | Ecodinâmica", layout="wide", initial_sidebar_state="expanded")

if "gdf_processado" not in st.session_state:
    st.session_state["gdf_processado"] = None
if "coluna_analise" not in st.session_state:
    st.session_state["coluna_analise"] = None
if "coluna_analise_sec" not in st.session_state:
    st.session_state["coluna_analise_sec"] = None
if "unidade_medida" not in st.session_state:
    st.session_state["unidade_medida"] = "Área (km²)"
if "nome_camada_ativa" not in st.session_state:
    st.session_state["nome_camada_ativa"] = ""

st.title("💧 WebGIS com Sistema de Inteligência Geográfica: Análise dos Sistemas Ambientais da Bacia Hidrográfica do Rio do Carmo-RN")
st.markdown("**Análise Espacial, Ecodinâmica e Geoprocessamento Dinâmico**")

# =====================================================================
# 2. RADAR DE ARQUIVOS (OTIMIZADO PARA NUVEM)
# =====================================================================
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent if BASE_DIR.name == "VSCODE" else BASE_DIR

DATA_DIR = REPO_DIR / "data"
if not DATA_DIR.exists():
    DATA_DIR = REPO_DIR 

todos_arquivos = list(DATA_DIR.rglob("*.geojson"))

if not todos_arquivos:
    st.error("⚠️ Nenhum arquivo '.geojson' encontrado na pasta data!")
    st.stop()

mapas_encontrados = {}
for arquivo in sorted(todos_arquivos):
    nome_legivel = arquivo.stem.replace("dados_ppgeo_bh_", "").replace("dados_", "").replace("_", " ").title()
    nome_legivel = nome_legivel.replace("Ana", "ANA").replace("Map Biomas", "MapBiomas").replace("Ibge", "IBGE")
    mapas_encontrados[nome_legivel] = arquivo

todas_imagens = []
for ext in ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']:
    todas_imagens.extend(DATA_DIR.rglob(ext))
    
mapas_estaticos = {f.stem.replace("_", " ").title(): f for f in sorted(todas_imagens)}

@st.cache_data(show_spinner=False)
def carregar_mapa(caminho): 
    return gpd.read_file(caminho)

def extrair_colunas_validas(gdf):
    return [col for col in gdf.columns if col.lower() not in ['geometry', 'id', 'fid', 'objectid', 'shape_area', 'shape_length']]

# =====================================================================
# 3. MOTOR UNIVERSAL DE CORES E IDENTIFICAÇÃO
# =====================================================================
cores_vulnerabilidade = {
    'MUITO BAIXA': '#1a9850', 'BAIXA': '#91cf60', 'MÉDIA': '#fee08b', 'MEDIA': '#fee08b',
    'ALTA': '#fc8d59', 'MUITO ALTA': '#d73027', 'SEM CLASSIFICAÇÃO': '#969696', 'SEM CLASSIFICACAO': '#969696'
}

def gerar_paleta(valores, nome_camada):
    valores_higienizados = valores.astype(str).fillna("SEM DADO")
    valores_unicos = sorted(list(set(valores_higienizados)))
    if "vulnerabilidade" in nome_camada.lower():
        return {str(v): cores_vulnerabilidade.get(str(v).strip().upper(), '#808080') for v in valores_unicos}
    
    paleta_plotly = px.colors.qualitative.Plotly + px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    return {str(v): paleta_plotly[i % len(paleta_plotly)] for i, v in enumerate(valores_unicos)}

def obter_coluna_real(gdf):
    colunas_prioritarias = ["CLASSE", "NOME_UNIDA", "NM_UNIDADE", "LEG_SINOT", "NM_MUN", "NOORIGINAL", "NOME_BACIA"]
    for col_pri in colunas_prioritarias:
        for col in gdf.columns:
            if col.upper() == col_pri: return col
    colunas_validas = [col for col in gdf.columns if col.lower() not in ['geometry', 'id', 'fid', 'objectid']]
    for col in colunas_validas:
        if gdf[col].dtype == 'object': return col
    return colunas_validas[0] if colunas_validas else None

# =====================================================================
# 4. PAINEL LATERAL (CONTROLE GERAL)
# =====================================================================
st.sidebar.header("⚙️ Configurações da Análise")
modo_analise = st.sidebar.radio(
    "Escolha o Modo de Navegação:", 
    ["1. Visão Geral (StoryMap)", "2. Laboratório de Geoprocessamento", "3. Atlas Cartográfico (Imagens)"]
)
st.sidebar.markdown("---")

# =====================================================================
# MODO 1: VISÃO GERAL (StoryMap Interativo)
# =====================================================================
if modo_analise == "1. Visão Geral (StoryMap)":
    
    with st.expander("📖 Metodologia: Ecodinâmica de Tricart", expanded=False):
        st.markdown("A modelagem de vulnerabilidade integra a dimensão do meio físico e a pressão antrópica por Álgebra de Mapas.")
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            st.markdown("**Vulnerabilidade Natural (VN):**")
            st.latex(r"VN = \frac{\text{Geomorfologia} + \text{Geologia} + \text{Pedologia} + \text{Vegetação} + \text{Uso e Cobertura do Solo}}{5}")
        with col_m2:
            st.markdown("**Vulnerabilidade Ambiental (VA):**")
            st.latex(r"VA = 0.2[\text{Geomorfologia}] + 0.1[\text{Geologia}] + 0.1[\text{Pedologia}] + 0.1[\text{Vegetação}] + 0.5[\text{Uso e Cobertura do Solo}]")

    st.markdown("---")
    
    bacia_key = next((k for k in mapas_encontrados.keys() if "bacia" in k.lower() or "limite" in k.lower()), list(mapas_encontrados.keys())[0])
    
    st.sidebar.subheader("🗺️ Controle de Camadas")
    camadas_alvo = st.sidebar.multiselect("Selecione os dados para visualizar:", list(mapas_encontrados.keys()), default=[bacia_key])
    
    estilos_camadas = {}
    
    for nome_camada in camadas_alvo:
        with st.sidebar.expander(f"🎨 Estilo: {nome_camada}", expanded=False):
            opacidade = st.slider("Transparência", 0.0, 1.0, 0.7, key=f"op_{nome_camada}")
            tipo_cor = st.radio("Cores:", ["Por Atributo", "Cor Única"], key=f"tc_{nome_camada}")
            
            gdf_temp = carregar_mapa(str(mapas_encontrados[nome_camada]))
            cols_validas = extrair_colunas_validas(gdf_temp)
            col_padrao = obter_coluna_real(gdf_temp)
            
            if tipo_cor == "Por Atributo":
                idx = cols_validas.index(col_padrao) if col_padrao in cols_validas else 0
                col_escolhida = st.selectbox("Atributo para colorir:", cols_validas, index=idx, key=f"col_{nome_camada}")
                cor_unica = None
            else:
                col_escolhida = None
                cor_unica = st.color_picker("Escolha a cor:", "#1f78b4" if "Bacia" in nome_camada else "#e31a1c", key=f"cp_{nome_camada}")
            
            estilos_camadas[nome_camada] = {
                "opacidade": opacidade, "tipo_cor": tipo_cor, "coluna": col_escolhida, "cor_unica": cor_unica
            }
    
    m_geral = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles=None)
    folium.TileLayer('CartoDB positron', name='Mapa Base (Claro)', control=True).add_to(m_geral)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Satélite (Google Hybrid)', overlay=False, control=True).add_to(m_geral)
    folium.TileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', attr='OpenTopoMap', name='Topografia (Curvas de Nível)', overlay=False, control=True).add_to(m_geral)

    tabelas_brutas = {}
    
    for nome_camada in camadas_alvo:
        gdf = carregar_mapa(str(mapas_encontrados[nome_camada])).copy()
        if gdf.crs is not None and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        estilo = estilos_camadas[nome_camada]
        opacidade = estilo["opacidade"]
        
        if estilo["tipo_cor"] == "Por Atributo":
            coluna_cor = estilo["coluna"]
            valores_para_paleta = gdf[coluna_cor].astype(str).fillna("SEM DADO")
            paleta = gerar_paleta(valores_para_paleta, nome_camada)
        else:
            coluna_cor = None
            paleta = None
            
        todas_colunas = extrair_colunas_validas(gdf)
        colunas_popup = todas_colunas[:5] 
        
        fg = folium.FeatureGroup(name=f"Camada: {nome_camada}")
        is_points = gdf.geometry.type.isin(['Point', 'MultiPoint']).any()

        if is_points:
            # RENDERIZAÇÃO DE PONTOS COMO LOSANGOS (DIAMONDS)
            for idx, row in gdf.iterrows():
                geom = row.geometry
                if geom is None: continue
                
                if paleta and coluna_cor:
                    valor = str(row.get(coluna_cor, '')).strip().upper()
                    cor_final = paleta.get(valor, '#808080')
                else:
                    cor_final = estilo["cor_unica"]
                
                html = ""
                for col_p in colunas_popup: html += f"<b>{col_p}:</b> {row.get(col_p, '')}<br>"
                
                coords = [[geom.y, geom.x]] if geom.type == 'Point' else [[p.y, p.x] for p in geom.geoms]
                for coord in coords:
                    folium.RegularPolygonMarker(
                        location=coord, number_of_sides=4, rotation=45, radius=7, # 4 lados rotacionado = Losango
                        color='#222222', weight=0.8, fill_color=cor_final, fill_opacity=opacidade,
                        popup=folium.Popup(html, max_width=300)
                    ).add_to(fg)
        else:
            def estilo_geral(feature, p=paleta, c=coluna_cor, cor_fixa=estilo["cor_unica"], op=opacidade):
                geom_type = feature['geometry']['type']
                if p and c:
                    valor = str(feature['properties'].get(c, '')).strip().upper()
                    cor_final = p.get(valor, '#808080')
                else: cor_final = cor_fixa
                    
                if geom_type in ['LineString', 'MultiLineString']: return {'color': cor_final, 'weight': 3, 'opacity': op}
                return {'fillColor': cor_final, 'color': '#222222', 'weight': 1, 'fillOpacity': op}

            folium.GeoJson(
                gdf, name=f"Camada: {nome_camada}", style_function=estilo_geral,
                highlight_function=lambda x: {'weight': 3, 'color': 'yellow'} if x['geometry']['type'] not in ['LineString', 'MultiLineString'] else {'weight': 5, 'color': 'red'},
                popup=folium.GeoJsonPopup(fields=colunas_popup, aliases=[f"<b>{c}</b>" for c in colunas_popup]) if colunas_popup else None
            ).add_to(fg)
        
        fg.add_to(m_geral)
        tabelas_brutas[nome_camada] = gdf.drop(columns=['geometry'])

    folium.LayerControl(collapsed=False).add_to(m_geral)
    
    st.subheader("Visualizador Exploratório")
    st.caption("👈 Clique nos elementos do mapa para abrir os atributos enxutos (Pop-up). Altere o mapa base e controle o estilo no menu lateral.")
    st.components.v1.html(m_geral._repr_html_(), height=550, scrolling=False)
    
    if tabelas_brutas:
        st.subheader("Tabelas de Dados Originais")
        abas_tabelas = st.tabs(list(tabelas_brutas.keys()))
        for i, nome in enumerate(tabelas_brutas.keys()):
            with abas_tabelas[i]:
                st.dataframe(tabelas_brutas[nome], use_container_width=True, hide_index=True)

# =====================================================================
# MODO 2: LABORATÓRIO DE GEOPROCESSAMENTO 
# =====================================================================
elif modo_analise == "2. Laboratório de Geoprocessamento":
    with st.expander("💡 Guia de Métodos e Álgebra Espacial (Dicas Técnicas)", expanded=False):
        st.markdown("""
        * **Intersecção (Strict Spatial Join):** Isola perfeitamente a tabela de atributos e as feições geográficas contidas rigorosamente dentro do perímetro delimitado.
        * **Buffer de Zona de Amortecimento:** Adiciona um raio ao redor da faca de recorte. Essencial para avaliar impactos marginais ou delimitar Áreas de Preservação Permanente (APP).
        * **Densidade de Kernel (KDE):** Gera um mapa de calor contínuo para pontos de ocorrência (Ex: Afloramentos, Nascentes).
        """)

    st.sidebar.subheader("🎯 1. Camada de Estudo")
    camada_alvo = st.sidebar.selectbox("O que será analisado/recortado?", list(mapas_encontrados.keys()), index=0)
    gdf_alvo_bruto = carregar_mapa(str(mapas_encontrados[camada_alvo]))
    col_alvo_selecionada = st.sidebar.selectbox("Escolha o atributo base da análise:", extrair_colunas_validas(gdf_alvo_bruto))
    
    cruzar_segundo = st.sidebar.checkbox("🔗 Cruzar com 2ª Análise Atributiva", value=False)
    col_alvo_secundada = None
    if cruzar_segundo: col_alvo_secundada = st.sidebar.selectbox("Segundo atributo para correlação:", [c for c in extrair_colunas_validas(gdf_alvo_bruto) if c != col_alvo_selecionada])

    st.sidebar.subheader("✂️ 2. Máscara de Recorte e Buffer")
    origem_mascara = st.sidebar.radio("Definir área de recorte:", ["📂 Usar Camada do Banco de Dados", "🖍️ Desenhar Área Personalizada"])
    
    buffer_metros = st.sidebar.number_input("Adicionar Buffer à Máscara (metros):", min_value=0, value=0, step=100)

    valor_faca, col_mask_selecionada = None, None
    if origem_mascara == "📂 Usar Camada do Banco de Dados":
        camada_mascara = st.sidebar.selectbox("Qual camada fará o corte?", list(mapas_encontrados.keys()), index=1)
        gdf_mask_bruto = carregar_mapa(str(mapas_encontrados[camada_mascara]))
        col_mask_selecionada = st.sidebar.selectbox("Coluna delimitadora de corte:", extrair_colunas_validas(gdf_mask_bruto))
        valores_recorte = sorted(gdf_mask_bruto[col_mask_selecionada].astype(str).unique())
        valor_faca = st.sidebar.selectbox(f"Selecione o limite exato de {col_mask_selecionada}:", valores_recorte)

    st.markdown("### 🗺️ Workspace Cartográfico Central")
    st.caption("Acompanhe aqui o desenho de áreas e o resultado dos geoprocessamentos.")

    m_lab = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles=None)
    folium.TileLayer('CartoDB positron', name='Mapa Base (Claro)', control=True).add_to(m_lab)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Satélite (Google Hybrid)', overlay=False, control=True).add_to(m_lab)

    if origem_mascara == "🖍️ Desenhar Área Personalizada":
        Draw(export=False, position='topleft').add_to(m_lab)

    if st.session_state["gdf_processado"] is not None:
        gdf_wgs84 = st.session_state["gdf_processado"].to_crs(epsg=4326).copy()
        coluna_foco = st.session_state["coluna_analise"]
        camada_nome = st.session_state["nome_camada_ativa"]
        
        gdf_wgs84[coluna_foco] = gdf_wgs84[coluna_foco].fillna("SEM DADO").astype(str).str.upper().str.strip()
        paleta_mestra = gerar_paleta(gdf_wgs84[coluna_foco], camada_nome)
        is_points_layer = gdf_wgs84.geometry.type.isin(['Point', 'MultiPoint']).any()
        cols_popup = extrair_colunas_validas(gdf_wgs84)[:5]
        
        fg_lab = folium.FeatureGroup(name=f"Análise: {camada_nome}")

        if is_points_layer:
            habilitar_kde = st.checkbox("🔥 Ativar Densidade de Kernel / Mapa de Calor", value=False)
            if habilitar_kde:
                heat_data = []
                for geom in gdf_wgs84.geometry:
                    if geom.type == 'Point': heat_data.append([geom.y, geom.x])
                    elif geom.type == 'MultiPoint': heat_data.extend([[p.y, p.x] for p in geom.geoms])
                HeatMap(heat_data, radius=18, blur=15, name="Kernel KDE").add_to(m_lab)

            for idx, row in gdf_wgs84.iterrows():
                geom = row.geometry
                if geom is None: continue
                valor = str(row.get(coluna_foco, '')).strip().upper()
                cor = paleta_mestra.get(valor, '#969696')
                
                html = ""
                for c in cols_popup: html += f"<b>{c}:</b> {row.get(c, '')}<br>"
                
                coords = [[geom.y, geom.x]] if geom.type == 'Point' else [[p.y, p.x] for p in geom.geoms]
                for coord in coords:
                    folium.RegularPolygonMarker(
                        location=coord, number_of_sides=4, rotation=45, radius=8, # Losango destacado
                        color='#111111', weight=1, fill_color=cor, fill_opacity=0.9,
                        tooltip=f"{coluna_foco}: {valor}",
                        popup=folium.Popup(html, max_width=300)
                    ).add_to(fg_lab)
        else:
            def estilo_lab(feature):
                geom_type = feature['geometry']['type']
                valor = str(feature['properties'].get(coluna_foco, '')).strip().upper()
                cor = paleta_mestra.get(valor, '#969696')
                if geom_type in ['LineString', 'MultiLineString']: return {'color': cor, 'weight': 4, 'opacity': 1}
                return {'fillColor': cor, 'color': '#222222', 'weight': 1, 'fillOpacity': 0.85}

            folium.GeoJson(
                gdf_wgs84, name="Resultado_Recortado", style_function=estilo_lab,
                popup=folium.GeoJsonPopup(fields=cols_popup, aliases=[f"<b>{c}</b>" for c in cols_popup]) if cols_popup else None,
                highlight_function=lambda x: {'weight': 3, 'color': 'white'} if x['geometry']['type'] not in ['LineString', 'MultiLineString'] else {'weight': 6, 'color': 'red'}
            ).add_to(fg_lab)

        fg_lab.add_to(m_lab)

    folium.LayerControl(collapsed=True).add_to(m_lab)
    draw_res = st_folium(m_lab, use_container_width=True, height=500, key="mapa_laboratorio_unico", return_on_hover=False)

    if st.sidebar.button("⚙️ Executar Geoprocessamento", type="primary"):
        with st.spinner("Cortando geometrias e recalculando tabelas..."):
            try:
                gdf_a = gdf_alvo_bruto.to_crs(epsg=31984)
                
                if origem_mascara == "📂 Usar Camada do Banco de Dados":
                    gdf_m = gdf_mask_bruto.to_crs(epsg=31984)
                    mascara_filtrada = gdf_m[gdf_m[col_mask_selecionada].astype(str) == str(valor_faca)][['geometry']]
                else:
                    if draw_res and draw_res.get("all_drawings"):
                        mascara_filtrada = gpd.GeoDataFrame.from_features(draw_res["all_drawings"], crs="EPSG:4326").to_crs(epsg=31984)
                    else:
                        st.sidebar.error("⚠️ Desenhe uma forma geométrica no mapa central primeiro!")
                        st.stop()

                if buffer_metros > 0: mascara_filtrada.geometry = mascara_filtrada.geometry.buffer(buffer_metros)

                gdf_cortado = gpd.overlay(gdf_a, mascara_filtrada, how="intersection")
                
                if gdf_cortado.empty:
                    st.sidebar.error("Sem intersecção física dentro dos limites determinados.")
                else:
                    if gdf_cortado.geometry.type.isin(['Polygon', 'MultiPolygon']).any():
                        gdf_cortado['Geometria_Calc'] = gdf_cortado.geometry.area / 10**6
                        st.session_state["unidade_medida"] = "Área (km²)"
                    else:
                        gdf_cortado['Geometria_Calc'] = gdf_cortado.geometry.length / 1000
                        st.session_state["unidade_medida"] = "Extensão (km)"
                        
                    st.session_state["gdf_processado"] = gdf_cortado
                    st.session_state["coluna_analise"] = col_alvo_selecionada
                    st.session_state["coluna_analise_sec"] = col_alvo_secundada if cruzar_segundo else None
                    st.session_state["nome_camada_ativa"] = camada_alvo
                    st.rerun() 
            except Exception as e:
                st.sidebar.error(f"Erro no geoprocessamento: {e}")

    # --- ÁREA DE ESTATÍSTICAS E TABELAS ---
    if st.session_state["gdf_processado"] is not None:
        gdf_trabalho = st.session_state["gdf_processado"].copy()
        coluna_foco = st.session_state["coluna_analise"]
        coluna_sec = st.session_state["coluna_analise_sec"]
        camada_nome = st.session_state["nome_camada_ativa"]
        und = st.session_state["unidade_medida"]

        if coluna_foco not in gdf_trabalho.columns:
            if f"{coluna_foco}_1" in gdf_trabalho.columns: coluna_foco = f"{coluna_foco}_1"
        if coluna_sec and coluna_sec not in gdf_trabalho.columns:
            if f"{coluna_sec}_1" in gdf_trabalho.columns: coluna_sec = f"{coluna_sec}_1"
        
        gdf_trabalho[coluna_foco] = gdf_trabalho[coluna_foco].fillna("SEM DADO").astype(str).str.upper().str.strip()
        if coluna_sec: gdf_trabalho[coluna_sec] = gdf_trabalho[coluna_sec].fillna("SEM DADO").astype(str).str.upper().str.strip()
        paleta_mestra = gerar_paleta(gdf_trabalho[coluna_foco], camada_nome)

        st.markdown("### 📊 Painel Estatístico Integrado")
        
        # Identifica colunas numéricas para Soma Total
        cols_numericas = [c for c in gdf_trabalho.columns if pd.api.types.is_numeric_dtype(gdf_trabalho[c]) and c.lower() not in ['id', 'fid', 'objectid', 'shape_area', 'shape_length', 'geometria_calc']]
        
        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1: tipo_grafico = st.selectbox("Formato Gráfico:", ["Rosca", "Pizza", "Barras Horizontais", "Barras Verticais", "Linhas", "Radar"])
        with col_ctrl2: filtro_usuario = st.multiselect("🔍 Filtrar Atributos:", options=sorted(list(gdf_trabalho[coluna_foco].unique())))
        with col_ctrl3:
            col_soma = None
            if cols_numericas:
                col_soma = st.selectbox("🧮 Somar Coluna Numérica (Opcional):", ["Nenhuma"] + cols_numericas)

        if filtro_usuario: gdf_trabalho = gdf_trabalho[gdf_trabalho[coluna_foco].isin(filtro_usuario)]

        if gdf_trabalho.geometry.type.isin(['Point', 'MultiPoint']).any():
            gdf_trabalho['Geometria_Calc'] = 1
            und = "Quantidade (Pontos)"

        if col_soma and col_soma != "Nenhuma":
            st.info(f"📍 **Destaque:** O somatório total do atributo **{col_soma}** na área recortada é **{gdf_trabalho[col_soma].sum():,.2f}**.")

        group_cols = [coluna_foco, coluna_sec] if coluna_sec else [coluna_foco]
        resumo_df = gdf_trabalho.groupby(group_cols)['Geometria_Calc'].sum().reset_index()
        resumo_df['%'] = (resumo_df['Geometria_Calc'] / resumo_df['Geometria_Calc'].sum()) * 100
        resumo_df = resumo_df.sort_values(by='Geometria_Calc', ascending=False)
        resumo_df['Rotulo'] = resumo_df['Geometria_Calc'].round(2).astype(str) + f" ({resumo_df['%'].round(1).astype(str)}%)"

        col_g1, col_g2 = st.columns([6, 4])
        with col_g1:
            if "Rosca" in tipo_grafico: fig = px.pie(resumo_df, values='Geometria_Calc', names=coluna_foco, hole=0.4, color=coluna_foco, color_discrete_map=paleta_mestra)
            elif "Pizza" in tipo_grafico: fig = px.pie(resumo_df, values='Geometria_Calc', names=coluna_foco, color=coluna_foco, color_discrete_map=paleta_mestra)
            elif "Horizontais" in tipo_grafico: fig = px.bar(resumo_df, x='Geometria_Calc', y=coluna_foco, color=coluna_sec if coluna_sec else coluna_foco, color_discrete_map=None if coluna_sec else paleta_mestra, barmode="group", text='Rotulo', orientation='h')
            elif "Verticais" in tipo_grafico: fig = px.bar(resumo_df, x=coluna_foco, y='Geometria_Calc', color=coluna_sec if coluna_sec else coluna_foco, color_discrete_map=None if coluna_sec else paleta_mestra, barmode="group", text='Rotulo', orientation='v')
            elif "Linhas" in tipo_grafico: fig = px.line(resumo_df, x=coluna_foco, y='Geometria_Calc', color=coluna_sec if coluna_sec else None, markers=True)
            elif "Radar" in tipo_grafico: fig = px.line_polar(resumo_df, r='Geometria_Calc', theta=coluna_foco, color=coluna_sec if coluna_sec else None, line_close=True)
            
            fig.update_layout(margin=dict(t=10, b=0, l=0, r=0))
            if "Rosca" in tipo_grafico or "Pizza" in tipo_grafico: fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)

        with col_g2:
            st.markdown(f"**Tabela Resumo Analítica**")
            df_visual = resumo_df[group_cols + ['Geometria_Calc', '%']].copy()
            df_visual.columns = group_cols + [und, 'Proporção (%)']
            
            df_visual[und] = df_visual[und].round(3)
            df_visual['Proporção (%)'] = df_visual['Proporção (%)'].round(2)
            
            # Adição automática da linha de TOTAL GERAL
            linha_total = pd.DataFrame([{
                group_cols[0]: "TOTAL GERAL",
                und: df_visual[und].sum(),
                'Proporção (%)': df_visual['Proporção (%)'].sum()
            }])
            if len(group_cols) > 1: linha_total[group_cols[1]] = "-"
            
            df_visual = pd.concat([df_visual, linha_total], ignore_index=True)
            st.dataframe(df_visual, hide_index=True, use_container_width=True)

        st.markdown("---")
        st.subheader("📥 Exportação e Tabelas Integrais")
        exp_col1, exp_col2, exp_col3 = st.columns(3)
        
        geojson_str = gdf_trabalho.to_crs(epsg=4326).to_json()
        exp_col1.download_button(label="🌍 Exportar GeoJSON", data=geojson_str, file_name=f"recorte.geojson", mime="application/json", use_container_width=True)
        
        try:
            kml_buffer = io.BytesIO()
            gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
            gdf_trabalho.to_crs(epsg=4326).to_file(kml_buffer, driver="KML")
            exp_col2.download_button(label="🗺️ Exportar KML (Google Earth)", data=kml_buffer.getvalue(), file_name=f"recorte.kml", mime="application/vnd.google-earth.kml+xml", use_container_width=True)
        except: exp_col2.info("KML disponível via conversão no QGIS.")

        try:
            shp_buffer = io.BytesIO()
            with zipfile.ZipFile(shp_buffer, 'w') as zf:
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    path_tmp = Path(tmpdir)
                    gdf_trabalho.to_file(path_tmp / "analise_gis.shp")
                    for file_path in path_tmp.iterdir(): zf.write(file_path, arcname=file_path.name)
            exp_col3.download_button(label="📦 Exportar Shapefile (.ZIP)", data=shp_buffer.getvalue(), file_name=f"recorte.zip", mime="application/zip", use_container_width=True)
        except: exp_col3.warning("Erro ao zipar Shapefile.")

        with st.expander(f"📋 Tabela de Atributos Combinada Integral"):
            st.dataframe(gdf_trabalho.drop(columns=['geometry']), hide_index=True, use_container_width=True)

# =====================================================================
# MODO 3: ATLAS CARTOGRÁFICO (Visualização de Imagens)
# =====================================================================
elif modo_analise == "3. Atlas Cartográfico (Imagens)":
    st.header("🗺️ Atlas Cartográfico (Mapas de Layout)")
    st.markdown("Visualize ou faça o download dos mapas estáticos em alta resolução produzidos para a pesquisa.")
    st.markdown("---")

    if not mapas_estaticos:
        st.info("💡 Nenhuma imagem (PNG, JPG, JPEG) foi encontrada na pasta data. Adicione seus arquivos para listagem automática.")
    else:
        col_selecao, col_download = st.columns([3, 1])
        
        with col_selecao:
            mapa_escolhido = st.selectbox("Selecione o mapa cartográfico para visualizar:", list(mapas_estaticos.keys()))
            caminho_imagem = mapas_estaticos[mapa_escolhido]
            
        with col_download:
            st.write("") 
            st.write("")
            with open(caminho_imagem, "rb") as file:
                tipo_mime = "image/png" if caminho_imagem.suffix.lower() == '.png' else "image/jpeg"
                st.download_button(
                    label="📥 Baixar Imagem em Alta",
                    data=file,
                    file_name=caminho_imagem.name,
                    mime=tipo_mime,
                    type="primary",
                    use_container_width=True
                )

        st.image(str(caminho_imagem), caption=f"Fonte: Dissertação - {mapa_escolhido}", use_container_width=True)

# =====================================================================
# RODAPÉ LATERAL: AUTOR E PESQUISA
# =====================================================================
st.sidebar.markdown("---")
st.sidebar.subheader("🎓 Sobre a Pesquisa")
st.sidebar.info("""
**Autor:** Herick Santos  
*Mestre em Geografia (UERN)* | *Geógrafo & Analista GIS*

Pesquisa de Mestrado sobre a Análise dos Sistemas Ambientais da Bacia Hidrográfica do Rio do Carmo (RN) utilizando Álgebra de Mapas com Ecodinâmica.

---
💼 [Acessar meu LinkedIn](https://www.linkedin.com/in/herick-santos-msc-3900a61b8/)  
📚 [Dissertação de Mestrado (UERN)](https://sucupira-legado.capes.gov.br/sucupira/public/consultas/coleta/trabalhoConclusao/viewTrabalhoConclusao.jsf?popup=true&id_trabalho=15178165)
""")
