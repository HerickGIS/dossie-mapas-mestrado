import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from pathlib import Path
import pandas as pd

# 1. Configuração inicial da página e Sessões de Memória (st.session_state)
st.set_page_config(page_title="Dashboard BHRC", layout="wide", initial_sidebar_state="expanded")

if "df_cruzamento" not in st.session_state:
    st.session_state["df_cruzamento"] = None
if "gdf_microanalise" not in st.session_state:
    st.session_state["gdf_microanalise"] = None
if "info_microanalise" not in st.session_state:
    st.session_state["info_microanalise"] = None

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

# =====================================================================
# 3. O RADAR AUTOMÁTICO DE ARQUIVOS
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
    "Bacia Delimitacao": "nome_bacia",
    "IBGE Cruzamento Carmo": "CLASSE",
    "Ibge Setores Rn": "NM_MUN" 
}

# 5. DICIONÁRIOS DE CORES
cores_vulnerabilidade = {
    'MUITO BAIXA': '#1a9850', 'BAIXA': '#91cf60', 'MÉDIA': '#fee08b', 'MEDIA': '#fee08b',
    'ALTA': '#fc8d59', 'MUITO ALTA': '#d73027', 'SEM CLASSIFICAÇÃO': '#969696', 'SEM CLASSIFICACAO': '#969696'
}
paleta_generica = ['#377eb8', '#984ea3', '#ff7f00', '#a65628', '#f781bf', '#1b9e77', '#d95f02', '#7570b3']

@st.cache_data(show_spinner=False)
def carregar_mapa(caminho_arquivo: str): 
    return gpd.read_file(caminho_arquivo)

# ---------------------------------------------------------------------
# FUNÇÃO BLINDADA PARA DESCOBRIR A COLUNA REAL (Ignora Case Sensitive)
# ---------------------------------------------------------------------
def obter_coluna_real(gdf, nome_camada):
    col_sugerida = colunas_principais.get(nome_camada)
    if col_sugerida:
        for col in gdf.columns:
            if col.lower() == col_sugerida.lower():
                return col
    
    col_fallback = next((col for col in gdf.columns if col.upper() in ["CLASSE", "VULNERABILIDADE", "NOME", "TIPO", "LEG_SINOT", "NM_UNIDADE", "NOME_UNIDA"]), None)
    if col_fallback: 
        return col_fallback
    
    colunas_validas = [col for col in gdf.columns if col != 'geometry']
    return colunas_validas[0] if colunas_validas else None

# =====================================================================
# 6. CRIAÇÃO DE 3 ABAS
# =====================================================================
aba_mapa, aba_cruzamento, aba_microanalise = st.tabs([
    "🗺️ Visualizador Principal", 
    "📊 Tabela Dinâmica (Join Espacial)",
    "✂️ Micro-Análise (Recorte Espacial)"
])

# ---------------------------------------------------------------------
# ABA 1: O VISUALIZADOR CARTOGRÁFICO
# ---------------------------------------------------------------------
with aba_mapa:
    st.sidebar.header("⚙️ Painel de Controle")
    camadas_selecionadas = st.sidebar.multiselect(
        "Ligue as variáveis no mapa:", list(mapas_encontrados.keys()),
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
            except: continue
                
            col_classe = obter_coluna_real(gdf, nome_camada)

            if col_classe and col_classe in gdf.columns:
                gdf[col_classe] = gdf[col_classe].astype(str).str.upper()
                classes_disponiveis = sorted(gdf[col_classe].unique())
                classes_filtradas = st.sidebar.multiselect(f"Filtrar {nome_camada}:", options=classes_disponiveis, default=classes_disponiveis)
                gdf = gdf[gdf[col_classe].isin(classes_filtradas)]

            dados_para_mapa[nome_camada] = {"gdf": gdf, "col_classe": col_classe}

            if col_classe and col_classe in gdf.columns and not gdf.empty:
                if "Vulnerabilidade" in nome_camada or "Uso" in nome_camada or "Geologia" in nome_camada:
                    gdf_calc = gdf.to_crs(epsg=31984) 
                    gdf_calc['Area_km2'] = gdf_calc.geometry.area / 10**6
                    resumo = gdf_calc.groupby(col_classe)['Area_km2'].sum().reset_index()
                    resumo['%'] = (resumo['Area_km2'] / resumo['Area_km2'].sum()) * 100
                    resumo['Area_km2'] = resumo['Area_km2'].round(2)
                    resumo['%'] = resumo['%'].round(2)
                    resumo['Rotulo_Grafico'] = resumo['Area_km2'].astype(str) + " km² (" + resumo['%'].astype(str) + "%)"
                    dados_para_graficos[nome_camada] = {"tipo": "area", "df": resumo, "coluna": col_classe}
                
                elif "IBGE" in nome_camada.upper():
                    col_pop = next((c for c in gdf.columns if 'pop' in c.lower() or c == 'v0001'), None)
                    if col_pop:
                        gdf[col_pop] = pd.to_numeric(gdf[col_pop], errors='coerce').fillna(0)
                        resumo_pop = gdf.groupby(col_classe)[col_pop].sum().reset_index()
                        resumo_pop.rename(columns={col_pop: 'Populacao'}, inplace=True)
                        resumo_pop['%'] = (resumo_pop['Populacao'] / resumo_pop['Populacao'].sum()) * 100
                        resumo_pop['%'] = resumo_pop['%'].round(2)
                        resumo_pop['Rotulo_Grafico'] = resumo_pop['Populacao'].astype(int).astype(str) + " hab. (" + resumo_pop['%'].astype(str) + "%)"
                        dados_para_graficos[nome_camada] = {"tipo": "populacao", "df": resumo_pop, "coluna": col_classe}

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

            def definir_estilo(feature, camada=nome_camada, coluna=col_classe, cor_idx=idx):
                if coluna and coluna in feature['properties']:
                    valor = str(feature['properties'].get(coluna, '')).strip().upper()
                    if "Vulnerabilidade" in camada or "IBGE" in camada.upper():
                        return {'fillColor': cores_vulnerabilidade.get(valor, '#969696'), 'color': '#000000', 'weight': 0.8 if "IBGE" in camada.upper() else 0.5, 'fillOpacity': 0.7}
                return {'fillColor': paleta_generica[cor_idx % len(paleta_generica)], 'color': '#333333', 'weight': 0.5, 'fillOpacity': 0.5}

            mostrar_tooltip = folium.GeoJsonTooltip(fields=[col_classe], aliases=["Atributo: "]) if col_classe and col_classe in gdf.columns else None
            folium.GeoJson(gdf, name=nome_camada, style_function=definir_estilo, highlight_function=lambda x: {'weight': 2, 'color': 'black', 'fillOpacity': 0.9}, tooltip=mostrar_tooltip).add_to(fg)
            fg.add_to(m)
        folium.LayerControl(collapsed=False).add_to(m)
        mapa_interativo = st_folium(m, use_container_width=True, height=600, return_on_hover=False)

    with col_dados:
        st.subheader("Painel de Inteligência")
        if dados_para_graficos:
            for nome_camada, info in dados_para_graficos.items():
                fig = px.bar(info["df"], x='Area_km2' if info["tipo"] == "area" else 'Populacao', y=info["coluna"], orientation='h', title=f"📊 Representatividade: {nome_camada}", color=info["coluna"], color_discrete_map=cores_vulnerabilidade, text='Rotulo_Grafico', custom_data=['%'])
                fig.update_traces(textposition='outside')
                fig.update_layout(showlegend=False, xaxis_title="Área (km²)" if info["tipo"] == "area" else "População (Hab.)", yaxis_title="", yaxis={'categoryorder':'total ascending'}, margin=dict(r=150))
                st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------
# ABA 2: MÓDULO TABELA DINÂMICA (JOIN)
# ---------------------------------------------------------------------
with aba_cruzamento:
    st.header("📊 Tabela Dinâmica (Spatial Join)")
    st.markdown("Sobrepõe duas camadas e transfere os atributos (Ideal para cruzar o IBGE com a Vulnerabilidade).")
    col_a, col_b, col_btn = st.columns([4, 4, 2])
    with col_a: camada_alvo_join = st.selectbox("1. Camada Alvo:", list(mapas_encontrados.keys()), index=0, key='join_alvo')
    with col_b: camada_recorte_join = st.selectbox("2. Camada Base:", list(mapas_encontrados.keys()), index=1, key='join_recorte')
    with col_btn: st.write(""); st.write(""); executar_join = st.button("🚀 Processar Join", type="primary", use_container_width=True)

    if executar_join:
        with st.spinner("Relacionando tabelas..."):
            gdf_alvo = carregar_mapa(str(mapas_encontrados[camada_alvo_join])).to_crs(epsg=31984)
            gdf_recorte = carregar_mapa(str(mapas_encontrados[camada_recorte_join])).to_crs(epsg=31984)
            st.session_state["df_cruzamento"] = gpd.sjoin(gdf_alvo, gdf_recorte, how="inner", predicate="intersects").drop(columns=['geometry'])
            st.success("✅ Relacionamento concluído!")

    if st.session_state["df_cruzamento"] is not None:
        df_join = st.session_state["df_cruzamento"]
        st.markdown("---")
        colunas_categoricas = df_join.select_dtypes(exclude=['number', 'geometry']).columns.tolist()
        colunas_numericas = df_join.select_dtypes(include=['number']).columns.tolist()
        
        c1, c2, c3 = st.columns(3)
        with c1: agrupar_por = st.selectbox("Agrupar por:", colunas_categoricas)
        with c2: valor_alvo = st.selectbox("Analisar:", ["Contagem"] + colunas_numericas)
        with c3: funcao = st.selectbox("Operação:", ["Soma", "Média"])

        df_pivot = df_join.groupby(agrupar_por).size().reset_index(name='Contagem') if valor_alvo == "Contagem" else df_join.groupby(agrupar_por)[valor_alvo].sum().reset_index() if funcao == "Soma" else df_join.groupby(agrupar_por)[valor_alvo].mean().reset_index()
        coluna_y = 'Contagem' if valor_alvo == "Contagem" else valor_alvo

        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(px.bar(df_pivot, x=agrupar_por, y=coluna_y, color=agrupar_por).update_layout(showlegend=False), use_container_width=True)
        with g2: st.plotly_chart(px.pie(df_pivot, values=coluna_y, names=agrupar_por, hole=0.4), use_container_width=True)

# ---------------------------------------------------------------------
# ABA 3: MICRO-ANÁLISE E RECORTES ESPACIAIS (O NOVO "CLIP") COM MEMÓRIA BLINDADA
# ---------------------------------------------------------------------
with aba_microanalise:
    st.header("✂️ Micro-Análise (Recorte Geométrico)")
    st.markdown("""
    Esta ferramenta recorta os polígonos de estudo usando os limites exatos de um atributo específico. 
    A área física será **recalculada na hora** baseada apenas nas fatias geométricas que sobrarem dentro do recorte.
    """)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("1. O que você quer analisar?")
        camada_estudo = st.selectbox("Camada de Estudo (Ex: Vegetação, Vulnerabilidade):", list(mapas_encontrados.keys()), index=0)
    
    with col2:
        st.subheader("2. Qual será a Faca de Recorte?")
        camada_mascara = st.selectbox("Camada Máscara (Ex: Municípios):", list(mapas_encontrados.keys()), index=1)
        
        gdf_mask_bruto = carregar_mapa(str(mapas_encontrados[camada_mascara]))
        col_filtro = obter_coluna_real(gdf_mask_bruto, camada_mascara)
        
        if col_filtro:
            valores_disponiveis = sorted(gdf_mask_bruto[col_filtro].astype(str).unique())
            valor_recorte = st.selectbox(f"Selecione o(a) {col_filtro} para o recorte:", valores_disponiveis)
        else:
            st.error("Não foi possível identificar uma coluna válida para filtragem nesta camada.")

    st.markdown("---")
    executar_clip = st.button("✂️ Executar Recorte Geométrico e Recalcular Área", type="primary", use_container_width=True)

    if executar_clip and col_filtro:
        with st.spinner(f"Fatiando polígonos e recalculando a área dentro de {valor_recorte}..."):
            try:
                gdf_alvo = carregar_mapa(str(mapas_encontrados[camada_estudo])).to_crs(epsg=31984)
                gdf_mask = carregar_mapa(str(mapas_encontrados[camada_mascara])).to_crs(epsg=31984)
                
                # 1. Isola a coluna certa do mapa alvo e remove as demais (evita erro de coluna duplicada)
                col_alvo_real = obter_coluna_real(gdf_alvo, camada_estudo)
                if col_alvo_real:
                    gdf_alvo = gdf_alvo[[col_alvo_real, 'geometry']]
                
                # 2. Filtra a máscara para ter apenas o polígono escolhido (Ex: Só Mossoró)
                mascara_filtrada = gdf_mask[gdf_mask[col_filtro].astype(str) == valor_recorte]
                mascara_filtrada = mascara_filtrada[['geometry']] # Mantém só a geometria da faca
                
                # 3. O Recorte Espacial (Intersection)
                gdf_recortado = gpd.overlay(gdf_alvo, mascara_filtrada, how="intersection")
                
                if gdf_recortado.empty:
                    st.warning(f"As camadas não se cruzam fisicamente ou não há dados de {camada_estudo} dentro de {valor_recorte}.")
                    st.session_state["gdf_microanalise"] = None
                else:
                    gdf_recortado['Nova_Area_km2'] = gdf_recortado.geometry.area / 10**6
                    st.session_state["gdf_microanalise"] = gdf_recortado
                    st.session_state["info_microanalise"] = {
                        "valor_recorte": valor_recorte, 
                        "col_alvo": col_alvo_real
                    }
            except Exception as e:
                st.error(f"Erro ao processar o recorte geométrico. Detalhes: {e}")

    # Fora do botão, o código desenha a tela usando a Memória
    if st.session_state["gdf_microanalise"] is not None:
        gdf_recortado = st.session_state["gdf_microanalise"]
        info_sessao = st.session_state["info_microanalise"]
        valor_recorte = info_sessao["valor_recorte"]
        col_alvo = info_sessao["col_alvo"]

        st.success(f"✅ Micro-análise em **{valor_recorte}** processada e ativa na sessão!")
        
        col_result_mapa, col_result_grafico = st.columns([6, 4])
        
        with col_result_grafico:
            resumo_clip = gdf_recortado.groupby(col_alvo)['Nova_Area_km2'].sum().reset_index()
            resumo_clip['%'] = (resumo_clip['Nova_Area_km2'] / resumo_clip['Nova_Area_km2'].sum()) * 100
            resumo_clip['Nova_Area_km2'] = resumo_clip['Nova_Area_km2'].round(2)
            resumo_clip['%'] = resumo_clip['%'].round(2)
            
            fig_clip = px.pie(
                resumo_clip, values='Nova_Area_km2', names=col_alvo, 
                title=f"Distribuição em {valor_recorte}",
                color=col_alvo, color_discrete_map=cores_vulnerabilidade, hole=0.3
            )
            fig_clip.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_clip, use_container_width=True)
            
            st.dataframe(resumo_clip.rename(columns={col_alvo: 'Classe', 'Nova_Area_km2': 'Área Física Real (km²)'}), hide_index=True)

        with col_result_mapa:
            gdf_recortado_wgs = gdf_recortado.to_crs(epsg=4326)
            centro_y = gdf_recortado_wgs.geometry.centroid.y.mean()
            centro_x = gdf_recortado_wgs.geometry.centroid.x.mean()
            
            m_clip = folium.Map(location=[centro_y, centro_x], zoom_start=10, tiles="CartoDB positron")
            
            def estilo_clip(feature):
                valor = str(feature['properties'].get(col_alvo, '')).strip().upper()
                cor = cores_vulnerabilidade.get(valor, paleta_generica[0])
                return {'fillColor': cor, 'color': 'black', 'weight': 1, 'fillOpacity': 0.8}
            
            folium.GeoJson(
                gdf_recortado_wgs,
                style_function=estilo_clip,
                tooltip=folium.GeoJsonTooltip(fields=[col_alvo], aliases=["Classe: "]) if col_alvo in gdf_recortado_wgs.columns else None
            ).add_to(m_clip)
            
            st_folium(m_clip, use_container_width=True, height=500, key="mapa_clip", return_on_hover=False)
