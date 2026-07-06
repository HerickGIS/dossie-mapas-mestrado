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
st.set_page_config(page_title="Dossiê BHRC | Ecodinâmica", layout="wide", initial_sidebar_state="expanded")

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
# 3. MOTOR UNIVERSAL DE CORES
# =====================================================================
cores_vulnerabilidade = {
    'MUITO BAIXA': '#1a9850', 'BAIXA': '#91cf60', 'MÉDIA': '#fee08b', 'MEDIA': '#fee08b',
    'ALTA': '#fc8d59', 'MUITO ALTA': '#d73027', 'SEM CLASSIFICAÇÃO': '#969696', 'SEM CLASSIFICACAO': '#969696'
}

def gerar_paleta(valores, nome_camada):
    valores_unicos = sorted(list(set(valores)))
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
# 4. PAINEL LATERAL (CONTROLE GERAL E GEOPROCESSAMENTO)
# =====================================================================
st.sidebar.header("⚙️ Configurações da Análise")
modo_analise = st.sidebar.radio("Escolha o Modo de Navegação:", ["1. Visão Geral (StoryMap)", "2. Laboratório de Geoprocessamento"])
st.sidebar.markdown("---")

# =====================================================================
# MODO 1: VISÃO GERAL (StoryMap)
# =====================================================================
if modo_analise == "1. Visão Geral (StoryMap)":
    col_metodo, col_autor = st.columns(2)
    with col_metodo:
        with st.expander("📖 Metodologia: Ecodinâmica de Tricart", expanded=False):
            st.markdown("A modelagem de vulnerabilidade integra a dimensão do meio físico e a pressão antrópica por Álgebra de Mapas.")
            st.markdown("**Vulnerabilidade Natural (VN):**")
            st.latex(r"VN = \frac{\text{Geomorfo} + \text{Geologia} + \text{Pedologia} + \text{Vegetação} + \text{Uso e Cobertura}}{5}")
            st.markdown("**Vulnerabilidade Ambiental (VA):**")
            st.latex(r"VA = 0.2[\text{Geomorfo}] + 0.1[\text{Geologia}] + 0.1[\text{Pedologia}] + 0.1[\text{Vegetação}] + 0.5[\text{Uso e Cobertura}]")
    with col_autor:
        with st.expander("🎓 Sobre o Autor e a Pesquisa", expanded=False):
            st.markdown("""
            **Desenvolvido por:** Herick Daniel Carvalho dos Santos  
            *Geógrafo e Analista GIS (Mestre em Geografia pela UERN)* Este painel é parte integrante da pesquisa com foco em **Insegurança Hídrica Domiciliar e Estudos de Bacias Hidrográficas** na zona rural de Mossoró e região.
            
            * 🔗 [Acessar a Dissertação Completa (Repositório)](#)
            * 📂 [Download do Atlas/Mapas Cartográficos (PDF)](#)
            """)

    st.markdown("---")
    st.sidebar.subheader("🗺️ Controle de Camadas")
    camadas_alvo = st.sidebar.multiselect("Selecione os dados para visualizar:", list(mapas_encontrados.keys()), default=[list(mapas_encontrados.keys())[0]])
    
    m_geral = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles=None)
    folium.TileLayer('CartoDB positron', name='Mapa Base (Claro)', control=True).add_to(m_geral)
    folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Satélite (Google Hybrid)', overlay=False, control=True).add_to(m_geral)
    folium.TileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', attr='OpenTopoMap', name='Topografia (Curvas de Nível)', overlay=False, control=True).add_to(m_geral)

    tabelas_brutas = {}
    for nome_camada in camadas_alvo:
        gdf = carregar_mapa(str(mapas_encontrados[nome_camada])).copy()
        if gdf.crs is not None and gdf.crs != "EPSG:4326":
            gdf = gdf.to_crs("EPSG:4326")
        
        col_padrao = obter_coluna_real(gdf)
        paleta = gerar_paleta(gdf[col_padrao], nome_camada) if col_padrao else {}
        colunas_popup = extrair_colunas_validas(gdf)
        
        fg = folium.FeatureGroup(name=nome_camada)
        
        def estilo_geral(feature, p=paleta, c=col_padrao):
            geom_type = feature['geometry']['type']
            if geom_type in ['LineString', 'MultiLineString']:
                return {'color': '#1f78b4', 'weight': 2, 'opacity': 0.8}
            valor = str(feature['properties'].get(c, '')).strip().upper()
            return {'fillColor': p.get(valor, '#333333'), 'color': '#000000', 'weight': 0.5, 'fillOpacity': 0.6}

        folium.GeoJson(
            gdf,
            name=f"Camada: {nome_camada}", # NOME LIMPO PARA EVITAR MACRO_ELEMENT
            style_function=estilo_geral,
            highlight_function=lambda x: {'weight': 3, 'color': 'yellow'} if x['geometry']['type'] not in ['LineString', 'MultiLineString'] else {'weight': 5, 'color': 'red'},
            popup=folium.GeoJsonPopup(fields=colunas_popup, aliases=[f"<b>{c}</b>" for c in colunas_popup], max_width=300) if colunas_popup else None
        ).add_to(fg)
        
        fg.add_to(m_geral)
        tabelas_brutas[nome_camada] = gdf.drop(columns=['geometry'])

    folium.LayerControl(collapsed=False).add_to(m_geral)
    
    st.subheader("Visualizador Exploratório")
    st.caption("👈 Clique nos elementos do mapa para abrir as informações (Pop-up). Altere o mapa base no ícone de camadas à direita.")
    st_folium(m_geral, use_container_width=True, height=550, return_on_hover=False)
    
    if tabelas_brutas:
        st.subheader("Tabelas de Dados Originais")
        abas_tabelas = st.tabs(list(tabelas_brutas.keys()))
        for i, nome in enumerate(tabelas_brutas.keys()):
            with abas_tabelas[i]:
                st.dataframe(tabelas_brutas[nome], use_container_width=True, hide_index=True)


# =====================================================================
# MODO 2: LABORATÓRIO DE GEOPROCESSAMENTO (Recorte, Join e Recálculo)
# =====================================================================
elif modo_analise == "2. Laboratório de Geoprocessamento":
    st.sidebar.subheader("🎯 1. Camada de Estudo")
    camada_alvo = st.sidebar.selectbox("O que será analisado/recortado?", list(mapas_encontrados.keys()), index=0)
    gdf_alvo_bruto = carregar_mapa(str(mapas_encontrados[camada_alvo]))
    col_alvo_selecionada = st.sidebar.selectbox("Escolha o atributo base da análise:", extrair_colunas_validas(gdf_alvo_bruto))
    
    st.sidebar.subheader("✂️ 2. Máscara de Recorte (Faca)")
    camada_mascara = st.sidebar.selectbox("Qual camada fará o corte?", list(mapas_encontrados.keys()), index=1)
    gdf_mask_bruto = carregar_mapa(str(mapas_encontrados[camada_mascara]))
    col_mask_selecionada = st.sidebar.selectbox("Coluna do polígono de corte:", extrair_colunas_validas(gdf_mask_bruto))
    
    valores_recorte = sorted(gdf_mask_bruto[col_mask_selecionada].astype(str).unique())
    valor_faca = st.sidebar.selectbox(f"Selecione o limite (ex: Nome do Município):", valores_recorte)

    if st.sidebar.button("✂️ Executar Geoprocessamento Avançado", type="primary"):
        with st.spinner("Realizando Intersecção Espacial..."):
            try:
                gdf_a = gdf_alvo_bruto.to_crs(epsg=31984)
                gdf_m = gdf_mask_bruto.to_crs(epsg=31984)
                
                mascara_filtrada = gdf_m[gdf_m[col_mask_selecionada].astype(str) == str(valor_faca)][['geometry']]
                gdf_cortado = gpd.overlay(gdf_a, mascara_filtrada, how="intersection")
                
                if gdf_cortado.empty:
                    st.sidebar.error("Sem intersecção física nestas áreas.")
                else:
                    if gdf_cortado.geometry.type.isin(['Polygon', 'MultiPolygon']).any():
                        gdf_cortado['Geometria_Calc'] = gdf_cortado.geometry.area / 10**6
                        st.session_state["unidade_medida"] = "Área (km²)"
                    else:
                        gdf_cortado['Geometria_Calc'] = gdf_cortado.geometry.length / 1000
                        st.session_state["unidade_medida"] = "Extensão (km)"
                        
                    st.session_state["gdf_processado"] = gdf_cortado
                    st.session_state["coluna_analise"] = col_alvo_selecionada
                    st.session_state["nome_camada_ativa"] = camada_alvo
            except Exception as e:
                st.sidebar.error(f"Erro no geoprocessamento: {e}")

    # --- RENDERIZAÇÃO DO LABORATÓRIO ---
    if st.session_state["gdf_processado"] is not None:
        gdf_trabalho = st.session_state["gdf_processado"].copy()
        coluna_foco = st.session_state["coluna_analise"]
        camada_nome = st.session_state["nome_camada_ativa"]
        und = st.session_state["unidade_medida"]
        
        gdf_trabalho[coluna_foco] = gdf_trabalho[coluna_foco].astype(str).str.upper().str.strip()

        st.subheader("Painel de Resultados: Intersecção e Recálculo")
        
        # Filtros Interativos
        controle_col1, controle_col2 = st.columns([1, 1])
        with controle_col1:
            tipo_grafico = st.selectbox("📊 Formato do Gráfico:", ["Rosca (Donut)", "Pizza Clássica", "Barras Horizontais"])
        with controle_col2:
            filtro_usuario = st.multiselect(
                "🔍 Filtrar Resultados? (Limpe para ver tudo)", 
                options=sorted(gdf_trabalho[coluna_foco].unique()),
                help="Selecione atributos específicos para recalcular os gráficos e isolá-los no mapa."
            )
        
        if filtro_usuario:
            gdf_trabalho = gdf_trabalho[gdf_trabalho[coluna_foco].isin(filtro_usuario)]
        
        paleta_mestra = gerar_paleta(gdf_trabalho[coluna_foco], camada_nome)

        # Geração da Tabela Resumo (Despoluída)
        resumo_df = gdf_trabalho.groupby(coluna_foco)['Geometria_Calc'].sum().reset_index()
        total_calc = resumo_df['Geometria_Calc'].sum()
        resumo_df['%'] = (resumo_df['Geometria_Calc'] / total_calc) * 100
        resumo_df = resumo_df.sort_values(by='Geometria_Calc', ascending=False)
        
        # Rótulo bonito para o gráfico
        resumo_df['Rotulo'] = resumo_df['Geometria_Calc'].round(2).astype(str) + f" {und.split(' ')[1]} (" + resumo_df['%'].round(1).astype(str) + "%)"

        col_mapa_lab, col_grafico_lab = st.columns([6, 4])
        
        with col_grafico_lab:
            # Gráfico de Alta Qualidade
            if "Rosca" in tipo_grafico:
                fig = px.pie(resumo_df, values='Geometria_Calc', names=coluna_foco, hole=0.4, color=coluna_foco, color_discrete_map=paleta_mestra)
                fig.update_traces(textposition='inside', textinfo='percent+label')
            elif "Pizza" in tipo_grafico:
                fig = px.pie(resumo_df, values='Geometria_Calc', names=coluna_foco, color=coluna_foco, color_discrete_map=paleta_mestra)
                fig.update_traces(textposition='inside', textinfo='percent+label')
            else:
                fig = px.bar(resumo_df, x='Geometria_Calc', y=coluna_foco, color=coluna_foco, color_discrete_map=paleta_mestra, text='Rotulo', orientation='h')
                fig.update_traces(textposition='outside')
                fig.update_layout(showlegend=False, xaxis_title=und, yaxis_title="")
            
            fig.update_layout(title=f"Proporção Recalculada", margin=dict(t=50, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela Simplificada (Livre de sujeira do Join)
            st.markdown(f"**Resumo Tabular ({und.split(' ')[0]})**")
            df_visual = resumo_df[[coluna_foco, 'Geometria_Calc', '%']].copy()
            df_visual.columns = ['Classe / Atributo', und, 'Proporção (%)']
            df_visual[und] = df_visual[und].round(3)
            df_visual['Proporção (%)'] = df_visual['Proporção (%)'].round(2)
            st.dataframe(df_visual, hide_index=True, use_container_width=True)

        with col_mapa_lab:
            gdf_wgs84 = gdf_trabalho.to_crs(epsg=4326)
            centro_y = gdf_wgs84.geometry.centroid.y.mean()
            centro_x = gdf_wgs84.geometry.centroid.x.mean()
            
            m_lab = folium.Map(location=[centro_y, centro_x], zoom_start=10, tiles=None)
            folium.TileLayer('CartoDB positron', name='Mapa Base (Claro)', control=True).add_to(m_lab)
            folium.TileLayer('https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}', attr='Google', name='Satélite (Google Hybrid)', overlay=False, control=True).add_to(m_lab)

            def estilo_lab(feature):
                geom_type = feature['geometry']['type']
                valor = str(feature['properties'].get(coluna_foco, '')).strip().upper()
                cor = paleta_mestra.get(valor, '#000000')
                if geom_type in ['LineString', 'MultiLineString']:
                    return {'color': cor, 'weight': 4, 'opacity': 1}
                return {'fillColor': cor, 'color': '#222222', 'weight': 1, 'fillOpacity': 0.85}

            # Nomeação limpa para evitar o erro macro_element_div_2
            fg_lab = folium.FeatureGroup(name=f"Análise: {camada_nome}")
            folium.GeoJson(
                gdf_wgs84,
                name="Resultado_Clip",
                style_function=estilo_lab,
                tooltip=folium.GeoJsonTooltip(fields=[coluna_foco], aliases=[f"{coluna_foco}: "]),
                highlight_function=lambda x: {'weight': 3, 'color': 'white'} if x['geometry']['type'] not in ['LineString', 'MultiLineString'] else {'weight': 6, 'color': 'red'}
            ).add_to(fg_lab)
            
            fg_lab.add_to(m_lab)
            folium.LayerControl(collapsed=False).add_to(m_lab)
            st_folium(m_lab, use_container_width=True, height=500, key="mapa_lab", return_on_hover=False)

        # Tabela Completa (Sanitizada)
        with st.expander(f"📋 Tabela Completa do Recorte (Spatial Join)"):
            st.caption("Atributos originais após o recorte. Colunas redundantes geradas pelo algoritmo foram removidas.")
            df_final = gdf_trabalho.drop(columns=['geometry']).copy()
            # Remove as colunas sujas geradas pelo geopandas overlay (ex: _1, _2)
            cols_limpas = [c for c in df_final.columns if not c.endswith('_1') and not c.endswith('_2')]
            df_final = df_final[cols_limpas]
            
            cols_ordem = ['Geometria_Calc', coluna_foco] + [c for c in df_final.columns if c not in ['Geometria_Calc', coluna_foco]]
            st.dataframe(df_final[cols_ordem].rename(columns={'Geometria_Calc': und}), hide_index=True, use_container_width=True)
