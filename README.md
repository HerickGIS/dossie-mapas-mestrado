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

1. **Visão Geral (Interação):**
   * **Múltiplas Camadas (Overlay):** Permite empilhar e cruzar visualmente diferentes planos de informação (Geologia, Geomorfologia, Pedologia, Vegetação, Drenagem, Municípios e Setores Censitários).
   * **Controle Granular Estético:** Ajuste individual de transparência por camada e alternância entre renderização por **Cor Única** ou **Por Atributo**.
   * **Basemaps Avançados:** Opções de alternância em tempo real entre mapas focados em topografia, satélite de alta resolução (Google Hybrid) e modos escuros/claros.

2. **Laboratório de Geoprocessamento (Clip & Join Dinâmico):**
   * **Intersecção Espacial Centralizada:** Executa fatiamentos geométricos (Clip) de qualquer camada alvo usando um polígono de interesse (ou desenho livre) como máscara de recorte.
   * **Recálculo de Geometria ao Vivo:** Recalcula automaticamente áreas (km²) ou contagens de pontos dentro do recorte.
   * **Análise de Kernel (KDE):** Gera mapas de calor dinâmicos para pontos de ocorrência.
   * **Painel Integrado para análises estatisticas e de dados:** Gráficos interativos (Rosca, Radar, Barras) sincronizados com o recorte, permitindo o cruzamento de variáveis e auditoria dos dados através da linha de "Total Geral".

3. **Atlas Cartográfico (Mapas de Layout):**
   * **Repositório de Alta Resolução:** Disponibiliza a coleção de mapas cartográficos temáticos elaborados durante a dissertação.
   * **Download Direto:** Acesso aos layouts prontos para impressão ou inserção em relatórios oficiais, servindo como referência estática e normatizada que contrasta com a análise exploratória dinâmica.

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

## 🚀 Como executar o projeto localmente

1. Clone este repositório:
```bash
git clone [https://github.com/HerickGIS/dossie-mapas-mestrado.git](https://github.com/HerickGIS/dossie-mapas-mestrado.git)
