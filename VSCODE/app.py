import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import plotly.express as px
from pathlib import Path
import pandas as pd

# 1. Configuração inicial da página (Layout Amplo)
st.set_page_config(page_title="Dashboard BHRC", layout="wide", initial_sidebar_state="expanded")

st.title("💧 Dashboard Analítico: Bacia Hidrográfica do Rio do Carmo")
st.markdown("**Sistema de Apoio à Decisão e Ecodinâmica (Metodologia de Jean Tricart)**")

# 2. O RADAR AUTOMÁTICO DE ARQUIVOS
BASE_DIR = Path(__file__).resolve().parent
REPO_DIR = BASE_DIR.parent if BASE_DIR.name == "VSCODE" else BASE_DIR

todos_arquivos = [f for f in REPO_DIR.rglob("*") if f.suffix.lower() == '.geojson']

if not todos_arquivos:
    st.error("⚠️ Nenhum arquivo '.geojson' encontrado no repositório!")
    st.stop()

# 3. Mapeamento das camadas disponíveis
mapas_encontrados = {}
for arquivo in sorted(todos_arquivos):
    nome_legivel = arquivo.stem.replace("dados_ppgeo_bh_", "").replace("_", " ").title()
    nome_legivel = nome_legivel.replace("Ana", "ANA").replace("Map Biomas", "MapBiomas")
    mapas_encontrados[nome_legivel] = arquivo

# 4. DICIONÁRIOS DE CORES (Tudo em Maiúsculo para cruzar perfeitamente com seus dados)
cores_vulnerabilidade = {
    'MUITO BAIXA': '#1a9850',       
    'BAIXA': '#91cf60',             
    'MÉDIA': '#fee08b',
    'MEDIA': '#fee08b', # Garantia caso falte acento
    'ALTA': '#fc8d59',              
    'MUITO ALTA': '#d73027',        
    'SEM CLASSIFICAÇÃO': '#969696', 
    'SEM CLASSIFICACAO': '#969696'
}
paleta_generica = ['#377eb8', '#984ea3', '#ff7f00', '#a65628', '#f781bf']

# 5. Barra Lateral (Apenas para seleção de camadas)
st.sidebar.header("⚙️ Controle de Camadas")
camadas_selecionadas = st.sidebar.multiselect(
    "Ligue e desligue as variáveis:", 
    list(mapas_encontrados.keys()),
    default=["Vulnerabilidade Natural"] if "Vulnerabilidade Natural" in mapas_encontrados else [list(mapas_encontrados.keys())[0]]
)

@st.cache_data(show_spinner=False)
def carregar_mapa(caminho_arquivo: str): 
    return gpd.read_file(caminho_arquivo)

# =====================================================================
# 6. DIVISÃO DA TELA: MAPA (Esquerda) e PAINEL DE DADOS (Direita)
# =====================================================================
col_mapa, col_dados = st.columns([6, 4]) # 60% da tela pro mapa, 40% pros gráficos

with col_mapa:
    st.subheader("Visualizador Cartográfico")
    m = folium.Map(location=[-5.6, -37.6], zoom_start=9, tiles="CartoDB positron")
    
    # Dicionário para guardar os dados e gerar os gráficos depois
    dados_para_graficos = {}

    if camadas_selecionadas:
        for idx, nome_camada in enumerate(camadas_selecionadas):
            caminho_do_mapa = mapas_encontrados[nome_camada]
            try:
                gdf = carregar_mapa(str(caminho_do_mapa))
            except Exception:
                st.error(f"⚠️ Falha ao ler {nome_camada}.")
                continue
                
            col_classe = next((col for col in gdf.columns if col.upper() in ["CLASSE", "VULNERABILIDADE", "NOME", "TIPO"]), None)
            if not col_classe and len(gdf.columns) > 1:
                col_classe = [col for col in gdf.columns if col != 'geometry'][0]

            # Processamento de Área para os Gráficos
            if col_classe and ("Vulnerabilidade" in nome_camada or "Uso" in nome_camada or "Geologia" in nome_camada):
                gdf_calc = gdf.to_crs(epsg=31984) # SIRGAS 2000 UTM 24S
                gdf_calc['Area_km2'] = gdf_calc.geometry.area / 10**6
                
                # Para evitar erros de case sensitive, força a coluna para maiúsculo
                gdf_calc[col_classe] = gdf_calc[col_classe].astype(str).str.upper()
                
                resumo = gdf_calc.groupby(col_classe)['Area_km2'].sum().reset_index()
                resumo['%'] = (resumo['Area_km2'] / resumo['Area_km2'].sum()) * 100
                dados_para_graficos[nome_camada] = {"df": resumo, "coluna": col_classe}

            if gdf.crs is not None and gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs("EPSG:4326")

            fg = folium.FeatureGroup(name=nome_camada)

            # A cor agora busca o valor convertido em maiúsculo
            def definir_estilo(feature, camada=nome_camada, coluna=col_classe, cor_idx=idx):
                valor = str(feature['properties'].get(coluna, '')).strip().upper()
                if "Vulnerabilidade" in camada:
                    cor = cores_vulnerabilidade.get(valor, '#969696')
                    return {'fillColor': cor, 'color': '#333333', 'weight': 0.5, 'fillOpacity': 0.7}
                
                cor_generica = paleta_generica[cor_idx % len(paleta_generica)]
                return {'fillColor': cor_generica, 'color': '#333333', 'weight': 0.5, 'fillOpacity': 0.5}

            # Interatividade de Highlight (O polígono acende ao passar o mouse)
            highlight_function = lambda x: {'weight': 2, 'color': 'black', 'fillOpacity': 0.9}

            folium.GeoJson(
                gdf,
                name=nome_camada,
                style_function=definir_estilo,
                highlight_function=highlight_function, # Destaca o polígono no hover!
                tooltip=folium.GeoJsonTooltip(fields=[col_classe], aliases=["Classe: "]) if col_classe else None
            ).add_to(fg)

            fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    
    # RENDERIZA O MAPA E CAPTURA EVENTOS (Cliques)
    # return_on_hover=False garante que ele só dispare ação quando você CLICAR
    mapa_interativo = st_folium(m, use_container_width=True, height=600, return_on_hover=False)

# =====================================================================
# PAINEL DE DADOS E GRÁFICOS (A "Comunicação" Direita)
# =====================================================================
with col_dados:
    st.subheader("Painel de Inteligência")
    
    # 1. COMUNICAÇÃO MAPA -> DASHBOARD (Leitura do Clique)
    clique = mapa_interativo.get("last_active_drawing")
    if clique:
        st.info("📍 **Área Selecionada no Mapa:**")
        propriedades = clique.get("properties", {})
        # Remove a chave obscura de estilo se houver
        propriedades_limpas = {k: v for k, v in propriedades.items() if k not in ['style', 'highlight']}
        st.json(propriedades_limpas)
    else:
        st.markdown("*Clique em qualquer polígono no mapa para ver seus atributos detalhados aqui.*")
    
    st.markdown("---")
    
    # 2. GRÁFICOS INTERATIVOS DO PLOTLY
    if dados_para_graficos:
        for nome_camada, info in dados_para_graficos.items():
            df_plot = info["df"]
            coluna_ref = info["coluna"]
            
            # Cria um gráfico de rosca (Donut Chart) incrível
            fig = px.pie(
                df_plot, 
                values='Area_km2', 
                names=coluna_ref, 
                hole=0.4,
                title=f"📊 Distribuição: {nome_camada}",
                color=coluna_ref,
                color_discrete_map=cores_vulnerabilidade # O gráfico usa as mesmas cores do mapa!
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            
            # Exibe o gráfico no Streamlit
            st.plotly_chart(fig, use_container_width=True)
            
            # Um mini-expander para quem quiser ver a tabela bruta
            with st.expander(f"Ver Tabela de {nome_camada}"):
                st.dataframe(df_plot, hide_index=True, use_container_width=True)
