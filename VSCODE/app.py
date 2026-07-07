import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import HeatMap, Draw, MousePosition, FloatImage
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
# Define a estrutura da página web no Streamlit
st.set_page_config(page_title="Dossiê BHRC | Ecodinâmica", layout="wide", initial_sidebar_state="expanded")

# Inicialização de variáveis globais de estado para manter dados na memória durante a navegação
if "gdf_processado" not in st.session_state: st.session_state["gdf_processado"] = None
if "coluna_analise" not in st.session_state: st.session_state["coluna_analise"] = None
if "coluna_analise_sec" not in st.session_state: st.session_state["coluna_analise_sec"] = None
if "unidade_medida" not in st.session_state: st.session_state["unidade_medida"] = "Área (km²)"
if "nome_camada_ativa" not in st.session_state: st.session_state["nome_camada_ativa"] = ""
if "buffer_geom" not in st.session_state: st.session_state["buffer_geom"] = None

st.title("💧 WebGIS com Sistema de Inteligência Geográfica: Análise dos Sistemas Ambientais da Bacia Hidrográfica do Rio do Carmo-RN")
st.markdown("**Análise Espacial, Ecodinâmica e Geoprocessamento Dinâmico**")

# =====================================================================
# 2. RADAR DE ARQUIVOS (OTIMIZADO PARA AMBIENTE CLOUD)
# =====================================================================
# Mapeia dinamicamente os arquivos na pasta 'data', ignorando o sistema do servidor
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent if BASE_DIR.name == "VSCODE" else BASE_DIR

DATA_DIR = REPO_DIR / "data"
if not DATA_DIR.exists(): DATA_DIR = REPO_DIR 

# Coleta de vetores GeoJSON
todos_arquivos = list(DATA_DIR.rglob("*.geojson"))
if not todos_arquivos:
    st.error("⚠️ Nenhum arquivo '.geojson' encontrado na pasta data!")
    st.stop()

# Tratamento de Strings para criar nomes limpos no menu
mapas_encontrados = {}
for arquivo in sorted(todos_arquivos):
    nome_legivel = arquivo.stem.replace("dados_ppgeo_bh_", "").replace("dados_", "").replace("_", " ").title()
    nome_legivel = nome_legivel.replace("Ana", "ANA").replace("Map Biomas", "MapBiomas").replace("Ibge", "IBGE")
    mapas_encontrados[nome_legivel] = arquivo

# Coleta de arquivos estáticos (Imagens/Layouts de Mapas)
todas_imagens = []
for ext in ['*.png', '*.jpg', '*.jpeg', '*.PNG', '*.JPG', '*.JPEG']:
    todas_imagens.extend(DATA_DIR.rglob(ext))
mapas_estaticos = {f.stem.replace("_", " ").title(): f for f in sorted(todas_imagens)}

# Função de carregamento com Cache para performance
@st.cache_data(show_spinner=False)
def carregar_mapa(caminho): return gpd.read_file(caminho)

# Filtro para evitar exibir colunas técnicas irrelevantes nos pop-ups
def extrair_colunas_validas(gdf):
    return [col for col in gdf.columns if col.lower() not in ['geometry', 'id', 'fid', 'objectid', 'shape_area', 'shape_length']]

# =====================================================================
# 3. MOTOR UNIVERSAL DE CORES E BASES CARTOGRÁFICAS
# =====================================================================
cores_vulnerabilidade = {
    'MUITO BAIXA': '#1a9850', 'BAIXA': '#91cf60', 'MÉDIA': '#fee08b', 'MEDIA': '#fee08b',
    'ALTA': '#fc8d59', 'MUITO ALTA': '#d73027', 'SEM CLASSIFICAÇÃO': '#969696', 'SEM CLASSIFICACAO': '#969696'
}

def gerar_paleta(valores, nome_camada):
    """Gera paletas de cores dinâmicas para gráficos e mapas baseadas nos atributos."""
    valores_higienizados = valores.astype(str).fillna("SEM DADO")
    valores_unicos = sorted(list(set(valores_higienizados)))
    # Força rampa de cores de semáforo para vulnerabilidade ambiental
    if "vulnerabilidade" in nome_camada.lower():
        return {str(v): cores_vulnerabilidade.get(str(v).strip().upper(), '#808080') for v in valores_unicos}
    # Paleta qualitativa universal para outras variáveis
    paleta_plotly = px.colors.qualitative.Plotly + px.colors.qualitative.Set3 + px.colors.qualitative.Pastel
    return {str(v): paleta_plotly[i % len(paleta_plotly)] for i, v in enumerate(valores_unicos)}

def obter_coluna_real(gdf):
    """Tenta descobrir automaticamente a coluna principal de um shapefile para colorir."""
    colunas_prioritarias = ["CLASSE", "NOME_UNIDA", "NM_UNIDADE", "LEG_SINOT", "NM_MUN", "NOORIGINAL", "NOME_BACIA"]
    for col_pri in colunas_prioritarias:
        for col in gdf.columns:
            if col.upper() == col_pri: return col
    colunas_validas = [col for col in gdf.columns if col.lower() not in ['geometry', 'id', 'fid', 'objectid']]
    for col in colunas_validas:
        if gdf[col].dtype == 'object': return col
    return colunas_validas[0] if colunas_validas else None

def adicionar_elementos_cartograficos(mapa_folium):
    """Adiciona Padronização Visual: Basemaps, Norte, Escala e Coordenadas do Mouse."""
    # Adição de Basemaps padronizados (Visão Satélite, Escuro, Claro e Arruamento)
    folium.TileLayer('CartoDB positron', name='Claro (Positron)', control=True).add_to(mapa_folium)
    folium.TileLayer('CartoDB dark_matter', name='Escuro (Dark Matter)', control=True).add_to(mapa_folium)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', attr='Google', name='Satélite Puro (Google)', overlay=False, control=True).add_to(mapa_folium)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Satélite Híbrido (Google)', overlay=False, control=True).add_to(mapa_folium)
    folium.TileLayer('OpenStreetMap', name='Street Maps (OSM)', control=True).add_to(mapa_folium)

    # Adição da Coordenada Geográfica dinâmica no ponteiro do mouse
    MousePosition(position='bottomright', separator=' | ', empty_string='Fora do Mapa', num_digits=5, prefix='Coordenada:').add_to(mapa_folium)

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
            st.latex(r"VN = \frac{\text{Geomorfologia} + \text{Geologia} + \text{Pedologia} + \text{Vegetação} + \text{Uso e Cobertura da Terra}}{5}")
        with col_m2:
            st.markdown("**Vulnerabilidade Ambiental (VA):**")
            st.latex(r"VA = 0.2[\text{Geomorfologia}] + 0.1x[\text{Geologia}] + 0.1x[\text{Pedologia}] + 0.1x[\text{Vegetação}] + 0.5x[\text{Uso e Cobertura da Terra}]")

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

            is_pts_camada = gdf_temp.geometry.type.isin(['Point', 'MultiPoint']).any()
            simbolo_pt = "🟢 Círculo"
            if is_pts_camada:
                simbolo_pt = st.selectbox("Símbolo do Ponto:", ["🟢 Círculo", "🔶 Losango", "◼️ Quadrado", "🔺 Triângulo"], key=f"simbolo_{nome_camada}")

            if tipo_cor == "Por Atributo":
                idx = cols_validas.index(col_padrao) if col_padrao in cols_validas else 0
                col_escolhida = st.selectbox("Atributo para colorir:", cols_validas, index=idx, key=f"col_{nome_camada}")
                cor_unica = None
            else:
                col_escolhida = None
                cor_unica = st.color_picker("Escolha a cor:", "#1f78b4" if "Bacia" in nome_camada else "#e31a1c", key=f"cp_{nome_camada}")

            estilos_camadas[nome_camada] = {"opacidade": opacidade, "tipo_cor": tipo_cor, "coluna": col_escolhida, "cor_unica": cor_unica, "simbolo": simbolo_pt}

    # Inicializa Mapa Principal com controle de escala nativo ativado
    m_geral = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles=None, control_scale=True)
    adicionar_elementos_cartograficos(m_geral)
    tabelas_brutas = {}

    for nome_camada in camadas_alvo:
        gdf = carregar_mapa(str(mapas_encontrados[nome_camada])).copy()
        if gdf.crs is not None and gdf.crs != "EPSG:4326": gdf = gdf.to_crs("EPSG:4326")

        estilo = estilos_camadas[nome_camada]
        opacidade, simbolo = estilo["opacidade"], estilo["simbolo"]

        if estilo["tipo_cor"] == "Por Atributo":
            coluna_cor = estilo["coluna"]
            paleta = gerar_paleta(gdf[coluna_cor].astype(str).fillna("SEM DADO"), nome_camada)
        else:
            coluna_cor, paleta = None, None

        colunas_popup = extrair_colunas_validas(gdf)[:5] 
        fg = folium.FeatureGroup(name=f"Camada: {nome_camada}")
        is_points = gdf.geometry.type.isin(['Point', 'MultiPoint']).any()

        if is_points:
            # Algoritmo de renderização geométrica para diferentes simbologias de Ponto
            for idx, row in gdf.iterrows():
                geom = row.geometry
                if geom is None: continue
                cor_final = paleta.get(str(row.get(coluna_cor, '')).strip().upper(), '#808080') if paleta and coluna_cor else estilo["cor_unica"]
                html = "".join([f"<b>{col_p}:</b> {row.get(col_p, '')}<br>" for col_p in colunas_popup])
                coords = [[geom.y, geom.x]] if geom.type == 'Point' else [[p.y, p.x] for p in geom.geoms]

                for coord in coords:
                    if "Losango" in simbolo: folium.RegularPolygonMarker(location=coord, number_of_sides=4, rotation=45, radius=7, color='#222222', weight=0.8, fill_color=cor_final, fill_opacity=opacidade, popup=folium.Popup(html, max_width=300)).add_to(fg)
                    elif "Quadrado" in simbolo: folium.RegularPolygonMarker(location=coord, number_of_sides=4, rotation=0, radius=6, color='#222222', weight=0.8, fill_color=cor_final, fill_opacity=opacidade, popup=folium.Popup(html, max_width=300)).add_to(fg)
                    elif "Triângulo" in simbolo: folium.RegularPolygonMarker(location=coord, number_of_sides=3, rotation=0, radius=7, color='#222222', weight=0.8, fill_color=cor_final, fill_opacity=opacidade, popup=folium.Popup(html, max_width=300)).add_to(fg)
                    else: folium.CircleMarker(location=coord, radius=5, color='#222222', weight=0.8, fill_color=cor_final, fill_opacity=opacidade, popup=folium.Popup(html, max_width=300)).add_to(fg)
        else:
            def estilo_geral(feature, p=paleta, c=coluna_cor, cor_fixa=estilo["cor_unica"], op=opacidade):
                geom_type = feature['geometry']['type']
                cor_final = p.get(str(feature['properties'].get(c, '')).strip().upper(), '#808080') if p and c else cor_fixa
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
    # O guia retorna atualizado para manter a fluidez de uso
    with st.expander("💡 Guia de Métodos e Álgebra Espacial (Dicas Técnicas)", expanded=False):
        st.markdown("""
        * **Intersecção (Spatial Join Restrito):** Isola a tabela de atributos e as feições geográficas rigorosamente dentro do perímetro de corte.
        * **Buffer de Zona de Amortecimento:** Adiciona um raio ao redor da faca de recorte. Útil para avaliar APP ou impactos marginais.
        * **Densidade de Kernel (KDE):** Gera mapa de calor para pontos de ocorrência (Ex: Afloramentos).
        * **Krigagem (Informação):** A Krigagem é uma interpolação complexa que cria superfícies (Raster) contínuas a partir de *Valores Z* (chuva, cota). Por ser um processo matemático preditivo denso, o WebGIS foca na visualização estatística Vetorial (Kernel e KDE). Para modelos Raster 3D, exporte o dado e utilize rotinas de `pykrige` no QGIS ou ArcGIS.
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

    # -----------------------------------------------------------------
    # PROCESSAMENTO PRINCIPAL DE ÁLGEBRA ESPACIAL (EXECUTION BLOCK)
    # -----------------------------------------------------------------
    # Tooltip clara para orientar o analista no clique
    if st.sidebar.button("⚙️ Executar Geoprocessamento", type="primary", help="Realiza a intersecção (Corte/Clip) entre a sua Camada de Estudo e a Área Desenhada ou Município, recalculando todas as estatísticas."):
        with st.spinner("Cortando geometrias e recalculando tabelas..."):
            try:
                gdf_a = gdf_alvo_bruto.to_crs(epsg=31984)

                # Monta a geometria da máscara
                if origem_mascara == "📂 Usar Camada do Banco de Dados":
                    gdf_m = gdf_mask_bruto.to_crs(epsg=31984)
                    mascara_filtrada = gdf_m[gdf_m[col_mask_selecionada].astype(str) == str(valor_faca)][['geometry']]
                else:
                    if st.session_state.get('last_draw'):
                        mascara_filtrada = gpd.GeoDataFrame.from_features(st.session_state['last_draw'], crs="EPSG:4326").to_crs(epsg=31984)
                    else:
                        st.sidebar.error("⚠️ Desenhe uma forma geométrica no mapa central primeiro e DEPOIS clique em Executar!")
                        st.stop()

                # Aplica o Buffer
                if buffer_metros > 0: mascara_filtrada.geometry = mascara_filtrada.geometry.buffer(buffer_metros)

                # Armazena a faca na memória para ser renderizada visivelmente no mapa
                st.session_state["buffer_geom"] = mascara_filtrada.to_crs(epsg=4326)

                # Corte Físico
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
            except Exception as e:
                st.sidebar.error(f"Erro no geoprocessamento: {e}")

    # -----------------------------------------------------------------
    # RENDERING DO LABORATÓRIO (PAINEL ESTATÍSTICO)
    # -----------------------------------------------------------------
    if st.session_state["gdf_processado"] is not None:
        gdf_trabalho = st.session_state["gdf_processado"].copy()
        coluna_foco = st.session_state["coluna_analise"]
        coluna_sec = st.session_state["coluna_analise_sec"]
        camada_nome = st.session_state["nome_camada_ativa"]
        und = st.session_state["unidade_medida"]

        # Blindagem _1 _2 das colunas
        if coluna_foco not in gdf_trabalho.columns:
            if f"{coluna_foco}_1" in gdf_trabalho.columns: coluna_foco = f"{coluna_foco}_1"
        if coluna_sec and coluna_sec not in gdf_trabalho.columns:
            if f"{coluna_sec}_1" in gdf_trabalho.columns: coluna_sec = f"{coluna_sec}_1"

        gdf_trabalho[coluna_foco] = gdf_trabalho[coluna_foco].fillna("SEM DADO").astype(str).str.upper().str.strip()
        if coluna_sec: gdf_trabalho[coluna_sec] = gdf_trabalho[coluna_sec].fillna("SEM DADO").astype(str).str.upper().str.strip()
        paleta_mestra = gerar_paleta(gdf_trabalho[coluna_foco], camada_nome)

        st.markdown("### 📊 Painel Estatístico Integrado")

        cols_numericas = [c for c in gdf_trabalho.columns if pd.api.types.is_numeric_dtype(gdf_trabalho[c]) and c.lower() not in ['id', 'fid', 'objectid', 'shape_area', 'shape_length', 'geometria_calc']]

        col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
        with col_ctrl1: tipo_grafico = st.selectbox("Formato Gráfico:", ["Rosca", "Pizza", "Barras Horizontais", "Barras Verticais", "Linhas", "Radar"])
        with col_ctrl2: filtro_usuario = st.multiselect("🔍 Filtrar Atributos:", options=sorted(list(gdf_trabalho[coluna_foco].unique())))
        with col_ctrl3:
            col_soma = None
            if cols_numericas: col_soma = st.selectbox("🧮 Somar Coluna Numérica (Opcional):", ["Nenhuma"] + cols_numericas)

        if filtro_usuario: gdf_trabalho = gdf_trabalho[gdf_trabalho[coluna_foco].isin(filtro_usuario)]

        if gdf_trabalho.geometry.type.isin(['Point', 'MultiPoint']).any():
            gdf_trabalho['Geometria_Calc'] = 1
            und = "Quantidade (Pontos)"

        if col_soma and col_soma != "Nenhuma":
            st.info(f"📍 **Destaque de Somatório:** O total acumulado do atributo **{col_soma}** é **{gdf_trabalho[col_soma].sum():,.2f}**.")

        group_cols = [coluna_foco, coluna_sec] if coluna_sec else [coluna_foco]
        resumo_df = gdf_trabalho.groupby(group_cols)['Geometria_Calc'].sum().reset_index()
        resumo_df['%'] = (resumo_df['Geometria_Calc'] / resumo_df['Geometria_Calc'].sum()) * 100
        resumo_df = resumo_df.sort_values(by='Geometria_Calc', ascending=False)

        # Correção do Rótulo do Gráfico para manter apenas a porcentagem elegante
        resumo_df['Rotulo'] = resumo_df.apply(lambda row: f"{row['Geometria_Calc']:.2f} {und.split(' ')[0]} ({row['%']:.1f}%)", axis=1)

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

            # Formatação do Negrito para a linha de TOTAL GERAL
            linha_total = pd.DataFrame([{group_cols[0]: "TOTAL GERAL", und: df_visual[und].sum(), 'Proporção (%)': df_visual['Proporção (%)'].sum()}])
            if len(group_cols) > 1: linha_total[group_cols[1]] = "-"
            df_visual = pd.concat([df_visual, linha_total], ignore_index=True)

            def highlight_last_row(s): return ['font-weight: bold' if s.name == len(df_visual)-1 else '' for v in s]
            st.dataframe(df_visual.style.apply(highlight_last_row, axis=1), hide_index=True, use_container_width=True)

    # -----------------------------------------------------------------
    # RENDERIZAÇÃO DO MAPA CENTRAL (Posicionado Abaixo do Gráfico)
    # -----------------------------------------------------------------
    st.markdown("### 🗺️ Workspace Cartográfico Central")
    st.caption("Acompanhe o mapa com sua área. Ferramentas de edição estão no canto esquerdo. **Desenhe, depois clique em Executar na barra lateral.**")

    # Controles Visuais Mapeados (Apenas se a camada já estiver processada e for de pontos)
    if st.session_state["gdf_processado"] is not None and st.session_state["gdf_processado"].geometry.type.isin(['Point', 'MultiPoint']).any():
        col_kde1, col_kde2 = st.columns(2)
        with col_kde1: habilitar_kde = st.checkbox("🔥 Ativar Densidade de Kernel / Mapa de Calor", value=False)
        with col_kde2: simbolo_lab = st.selectbox("📌 Formato do Ponto Cartográfico:", ["🟢 Círculo", "🔶 Losango", "◼️ Quadrado", "🔺 Triângulo"])

    m_lab = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles=None, control_scale=True)
    adicionar_elementos_cartograficos(m_lab)

    if origem_mascara == "🖍️ Desenhar Área Personalizada":
        Draw(export=False, position='topleft').add_to(m_lab)

    # Plotagem do Buffer de Máscara (Visibilidade para o Usuário)
    if st.session_state["buffer_geom"] is not None:
        def style_faca(x): return {'color': 'red', 'weight': 2, 'dashArray': '5, 5', 'fillOpacity': 0.05}
        folium.GeoJson(st.session_state["buffer_geom"], name="Área de Recorte / Buffer", style_function=style_faca).add_to(m_lab)

    # Plotagem do Recorte Processado
    if st.session_state["gdf_processado"] is not None:
        gdf_wgs84 = gdf_trabalho.to_crs(epsg=4326)
        cols_popup = extrair_colunas_validas(gdf_wgs84)[:5]
        fg_lab = folium.FeatureGroup(name=f"Análise Recortada: {camada_nome}")

        if gdf_wgs84.geometry.type.isin(['Point', 'MultiPoint']).any():
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
                html = "".join([f"<b>{c}:</b> {row.get(c, '')}<br>" for c in cols_popup])
                coords = [[geom.y, geom.x]] if geom.type == 'Point' else [[p.y, p.x] for p in geom.geoms]

                for coord in coords:
                    if "Losango" in simbolo_lab: folium.RegularPolygonMarker(location=coord, number_of_sides=4, rotation=45, radius=7, color='#111111', weight=1, fill_color=cor, fill_opacity=0.9, popup=folium.Popup(html, max_width=300)).add_to(fg_lab)
                    elif "Quadrado" in simbolo_lab: folium.RegularPolygonMarker(location=coord, number_of_sides=4, rotation=0, radius=6, color='#111111', weight=1, fill_color=cor, fill_opacity=0.9, popup=folium.Popup(html, max_width=300)).add_to(fg_lab)
                    elif "Triângulo" in simbolo_lab: folium.RegularPolygonMarker(location=coord, number_of_sides=3, rotation=0, radius=7, color='#111111', weight=1, fill_color=cor, fill_opacity=0.9, popup=folium.Popup(html, max_width=300)).add_to(fg_lab)
                    else: folium.CircleMarker(location=coord, radius=5, color='#111111', weight=1, fill_color=cor, fill_opacity=0.9, popup=folium.Popup(html, max_width=300)).add_to(fg_lab)
        else:
            def estilo_lab(feature):
                cor = paleta_mestra.get(str(feature['properties'].get(coluna_foco, '')).strip().upper(), '#969696')
                if feature['geometry']['type'] in ['LineString', 'MultiLineString']: return {'color': cor, 'weight': 4, 'opacity': 1}
                return {'fillColor': cor, 'color': '#222222', 'weight': 1, 'fillOpacity': 0.85}

            folium.GeoJson(
                gdf_wgs84, name="Resultado_Recortado", style_function=estilo_lab,
                popup=folium.GeoJsonPopup(fields=cols_popup, aliases=[f"<b>{c}</b>" for c in cols_popup]) if cols_popup else None,
                highlight_function=lambda x: {'weight': 3, 'color': 'white'} if x['geometry']['type'] not in ['LineString', 'MultiLineString'] else {'weight': 6, 'color': 'red'}
            ).add_to(fg_lab)

        fg_lab.add_to(m_lab)

    folium.LayerControl(collapsed=True).add_to(m_lab)

    # Captura o mapa para que o desenho seja monitorado
    draw_res = st_folium(m_lab, use_container_width=True, height=500, key="mapa_laboratorio_unico", return_on_hover=False)

    # Salva o desenho na memória em tempo real para permitir recorte posterior
    if origem_mascara == "🖍️ Desenhar Área Personalizada" and draw_res and draw_res.get("all_drawings"):
        st.session_state['last_draw'] = draw_res["all_drawings"]

    # -----------------------------------------------------------------
    # SEÇÃO INFERIOR: DOWNLOADS DE DADOS AUDITADOS
    # -----------------------------------------------------------------
    if st.session_state["gdf_processado"] is not None:
        st.markdown("---")
        st.subheader("📥 Exportação Cartográfica do Recorte")
        exp_col1, exp_col2 = st.columns(2)

        geojson_str = gdf_trabalho.to_crs(epsg=4326).to_json()
        exp_col1.download_button(label="🌍 Exportar GeoJSON", data=geojson_str, file_name=f"recorte.geojson", mime="application/json", use_container_width=True)

        try:
            shp_buffer = io.BytesIO()
            with zipfile.ZipFile(shp_buffer, 'w') as zf:
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    path_tmp = Path(tmpdir)
                    gdf_trabalho.to_file(path_tmp / "analise_gis.shp")
                    for file_path in path_tmp.iterdir(): zf.write(file_path, arcname=file_path.name)
            exp_col2.download_button(label="📦 Exportar Shapefile (.ZIP)", data=shp_buffer.getvalue(), file_name=f"recorte.zip", mime="application/zip", use_container_width=True)
        except: 
            exp_col2.warning("Erro ao zipar Shapefile.")

        with st.expander(f"📋 Tabela de Atributos Combinada Integral (Auditoria de Atributos)"):
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
