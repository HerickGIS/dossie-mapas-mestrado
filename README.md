# 🗺️ Dossiê Dinâmico: Os Sistemas Ambientais da Bacia Hidrográfica do Rio do Carmo (RN)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)
![GeoPandas](https://img.shields.io/badge/GeoPandas-Spatial_Analysis-green.svg)
![Status](https://img.shields.io/badge/Status-Concluído-brightgreen.svg)

## 📌 Sobre o Projeto
Esta aplicação transforma o paradigma dos mapas estáticos em PDF, permitindo que pesquisadores, gestores, empresas que realizam estudos ambientais, bem como a sociedade interajam diretamente com dados geoespaciais. O projeto nasceu da minha experiência no Mestrado, onde, após uma extensa pesquisa, percebi o limite das análises impressas: ao final de 180 páginas, os dados tornavam-se estáticos, impedindo novas explorações ou insights.

A partir dessa reflexão, surgiu a proposta de criar uma plataforma viva. Utilizando Python e um ecossistema robusto de bibliotecas para análise de dados, desenvolvi esta ferramenta não apenas para visualizar a Bacia Hidrográfica do Rio do Carmo (BHRC), mas para permitir a continuidade da análise, transformando dados em inteligência geográfica acessível e dinâmica. Como esse repositório é público, você mesmo pode utilizar em sua pesquisa.

🔗 **[Acesse o Dashboard Interativo Aqui](https://dossie-mapas-mestrado-herick-santos.streamlit.app)**

## 🎯 Principais Funcionalidades

O dashboard está estruturado em três vertentes operacionais complementares na mesma interface:

1. **Visão Geral (Exploração Cartográfica):**
   * **Enquadramento Inteligente:** O sistema lê a camada base e calcula automaticamente o centroide da bacia, centralizando o mapa de forma dinâmica.
   * **Múltiplas Camadas (Overlay):** Permite empilhar e cruzar visualmente diferentes planos de informação (Geologia, Geomorfologia, Pedologia, Vegetação, Drenagem, Municípios e Setores Censitários).
   * **Controle Granular e Simbologia:** Ajuste individual de transparência, renderização por atributo com paletas de cores otimizadas e escolha de simbologia cartográfica precisa para pontos (Círculos, Losangos, Quadrados e Triângulos).
   * **Basemaps Avançados:** Alternância em tempo real entre topografia (Curvas de Nível), satélite de alta resolução (Google Hybrid), Street Maps e modos escuro/claro.

2. **Laboratório de Geoprocessamento (Análise de Dados):**
   * **Filtro Avançado (SQL):** Construtor de equações lógicas que permite fatiar os dados brutos e filtrar categorias ou valores matemáticos *antes* de aplicar o recorte geográfico.
   * **Intersecção Espacial Centralizada (Clip):** Executa fatiamentos geométricos de qualquer camada alvo usando o limite de um município ou um desenho vetorial livre feito pelo usuário como máscara de recorte.
   * **Recálculo de Geometria ao Vivo:** Recalcula automaticamente a área (km²) de polígonos, extensão (km) de linhas ou contagens estatísticas de pontos contidos estritamente dentro do novo recorte.
   * **Estatística:** Gráficos interativos (Rosca, Radar, Barras e Linhas) com agrupamento de múltiplas variáveis. Inclui auditoria de dados com linha de "Total Geral" e detecção de métricas para somatório numérico automático (ex: volume, população).
   * **Exportação de Dados Auditados:** Download instantâneo da área analisada em formatos abertos (`GeoJSON`) ou proprietários consolidados (`Shapefile` / `.zip`).
   * **Densidade de Kernel (KDE):** Gera mapa de calor para pontos de ocorrência (ex: afloramentos etc).

3. **Atlas Cartográfico (Mapas de Layout):**
   * **Repositório de Alta Resolução:** Disponibiliza a coleção de mapas cartográficos temáticos elaborados durante a dissertação.
   * **Download Direto:** Acesso aos layouts prontos para impressão ou inserção em relatórios oficiais, servindo como referência estática e normatizada que contrasta com a análise exploratória dinâmica da plataforma.

## 🛠️ Tecnologias Utilizadas

* **[Streamlit](https://streamlit.io/):** Framework para estruturação da aplicação web.
* **[GeoPandas](https://geopandas.org/):** Motor de geoprocessamento (projeções e álgebra espacial).
* **[Folium](https://python-visualization.github.io/folium/):** Renderização de mapas interativos Leaflet.
* **[Plotly Express](https://plotly.com/python/):** Criação de gráficos dinâmicos de alta performance.
* **[Pandas](https://pandas.pydata.org/):** Manipulação e agregação tabular.

## 📁 Estrutura do Repositório

Para o funcionamento do "radar automático de dados", mantenha a organização abaixo:

```text
├── data/
│   ├── [Arquivos .geojson do projeto]
│   └── [Imagens/Atlas para o Módulo 3]
├── VSCODE/
│   └── app.py
├── requirements.txt
└── README.md

🚀 Como executar o projeto localmente
Clone este repositório:

Bash
git clone [https://github.com/HerickGIS/dossie-mapas-mestrado.git](https://github.com/HerickGIS/dossie-mapas-mestrado.git)
Acesse a pasta do projeto:

Bash
cd dossie-mapas-mestrado
Instale as bibliotecas necessárias:

Bash
pip install -r requirements.txt
Execute a aplicação WebGIS:

Bash
streamlit run VSCODE/app.py

Desenvolvido por Herick Santos | Mestre em Geografia (UERN) | Geógrafo & Analista GIS
