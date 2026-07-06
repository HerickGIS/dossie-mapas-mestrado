# 🗺️ Dossiê Dinâmico: Sistemas Ambientais da Bacia Hidrográfica do Rio do Carmo (RN)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)
![GeoPandas](https://img.shields.io/badge/GeoPandas-Spatial_Analysis-green.svg)
![Status](https://img.shields.io/badge/Status-Concluído-brightgreen.svg)

## 📌 Sobre o Projeto
Este repositório contém um Dashboard interativo desenvolvido para materializar os resultados da dissertação de mestrado focada na análise da **Bacia Hidrográfica do Rio do Carmo (BHRC)**, localizada no semiárido do Rio Grande do Norte.

O objetivo desta aplicação é ir além dos mapas estáticos em PDF, permitindo que pesquisadores, gestores públicos e o público em geral interajam com os dados geoespaciais, explorem as unidades de paisagem e compreendam as dinâmicas de uso e ocupação da terra na região.

🔗 **[Acesse o Dashboard Interativo Aqui] (Link para Projeto no Streamlit(https://dossie-mapas-mestrado-dqusahnjwhsbfgxoqddx3u.streamlit.app/))**

## 🎯 Principais Funcionalidades (O que o Dashboard faz) 

O dashboard está estruturado em duas vertentes operacionais complementares na mesma interface:

1. **Visão Geral (StoryMap Interativo):**
   * **Múltiplas Camadas (Overlay):** Permite empilhar e cruzar visualmente diferentes planos de informação (Geologia, Geomorfologia, Pedologia, Vegetação, Drenagem ANA, Municípios e Setores Censitários).
   * **Controle Granular Estético:** Ajuste individual de transparência por camada e alternância entre renderização por **Cor Única** ou **Por Atributo** (sincronizando os dados do arquivo diretamente com o mapa).
   * **Basemaps Avançados:** Opções de alternância em tempo real entre mapas bases focados em topografia (curvas de nível) e imagens de satélite de alta resolução (Google Hybrid).
   * **Pop-ups e Ícones Enxutos:** Consulta de atributos nativos de pontos, linhas e polígonos diretamente na tela através de pop-ups flutuantes otimizados.

2. **Laboratório de Geoprocessamento (Clip & Join Dinâmico):**
   * **Intersecção Espacial Centralizada (Overlay Intersection):** Executa fatiamentos geométricos de qualquer camada alvo usando um polígono de interesse como máscara de recorte (faca).
   * **Recálculo de Geometria ao Vivo:** Calcula automaticamente as novas áreas físicas (em km²) ou extensões de linhas (em km) que restaram estritamente dentro do perímetro recortado.
   * **Tabela Dinâmica e Sincronização Visual:** Gera automaticamente gráficos de rosca, pizza ou barras verticais/horizontais compartilhando exatamente a mesma paleta de cores do mapa, com a opção de filtragem rápida de classes pelo usuário.

O pipeline de desenvolvimento do projeto utiliza ferramentas de vanguarda no ecossistema de Data Science e Geoprocessamento open-source:

* **[Streamlit](https://streamlit.io/):** Framework para estruturação da aplicação web e reatividade da interface.
* **[GeoPandas](https://geopandas.org/):** Motor de geoprocessamento responsável pelas projeções cartográficas e operações topológicas (`spatial joins` e `overlays`).
* **[Folium](https://python-visualization.github.io/folium/) & [Streamlit-Folium](https://github.com/randyzwitch/streamlit-folium):** Renderização cartográfica interativa baseada na biblioteca JavaScript Leaflet.
* **[Plotly Express](https://plotly.com/python/):** Criação dos gráficos dinâmicos com suporte a tooltips e renderização vetorial.
* **[Pandas](https://pandas.pydata.org/):** Manipulação, agrupamento e filtragem das tabelas de atributos estruturadas.

## 📁 Estrutura do Repositório

Para o correto funcionamento do "radar automático de dados", o repositório deve seguir a organização estrutural abaixo:

```text
├── data/
│   ├── dados_ppgeo_bh_bacia_delimitacao.geojson
│   ├── dados_ppgeo_bh_vulnerabilidade_ambiental.geojson
│   ├── dados_ppgeo_bh_municipios.geojson
│   └── [outros arquivos .geojson do inventário...]
├── VSCODE/
│   └── app.py
├── requirements.txt
└── README.md


## 🚀 Como executar o projeto localmente

1. Clone este repositório:
```bash
git clone [https://github.com/HerickGIS/dossie-mapas-mestrado.git](https://github.com/HerickGIS/dossie-mapas-mestrado.git)
