# 🗺️ Dossiê Dinâmico: Sistemas Ambientais da Bacia Hidrográfica do Rio do Carmo (RN)

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red.svg)
![GeoPandas](https://img.shields.io/badge/GeoPandas-Spatial_Analysis-green.svg)
![Status](https://img.shields.io/badge/Status-Concluído-brightgreen.svg)

## 📌 Sobre o Projeto
Este repositório contém um Dashboard interativo desenvolvido para materializar os resultados da dissertação de mestrado focada na análise da **Bacia Hidrográfica do Rio do Carmo (BHRC)**, localizada no semiárido do Rio Grande do Norte.

O objetivo desta aplicação é ir além dos mapas estáticos em PDF, permitindo que pesquisadores, gestores públicos e o público em geral interajam com os dados geoespaciais, explorem as unidades de paisagem e compreendam as dinâmicas de uso e ocupação da terra na região.

🔗 **[Acesse o Dashboard Interativo Aqui] (Insira_o_link_do_streamlit_aqui_depois_do_deploy)**

## 🎯 Principais Funcionalidades (O que o Dashboard faz)
- **Inventário Biofísico Interativo:** Navegação dinâmica por camadas de Geologia, Geomorfologia, Pedologia, Vegetação e Uso e Cobertura da Terra (dados do MapBiomas 2021).
- **Análise de Vulnerabilidade:** Espacialização da Ecodinâmica de Tricart, permitindo a comparação visual e estatística entre a **Vulnerabilidade Natural** (equilíbrio morfogênese/pedogênese) e a **Vulnerabilidade Ambiental** (peso das ações antrópicas).
- **Recortes por Sistemas Ambientais:** Filtros integrados para isolar e analisar compartimentos específicos, como os Tabuleiros da Chapada do Apodi ou a Depressão Sertaneja Setentrional.
- **Gráficos Integrados:** Geração automática de gráficos quantitativos (Plotly) que respondem à interação com o mapa (Leaflet/Folium).

## 🛠️ Tecnologias e Bibliotecas Utilizadas
A arquitetura do projeto foi construída utilizando o ecossistema open-source de Python para análise e visualização de dados espaciais:
* **Streamlit:** Construção da interface web e roteamento interativo.
* **GeoPandas & Pandas:** Manipulação das tabelas de atributos e processamento das geometrias.
* **Folium & Streamlit-Folium:** Renderização dos mapas interativos baseados em Leaflet.
* **Plotly Express:** Geração de gráficos analíticos e painéis de indicadores.

## 🚀 Como executar o projeto localmente

1. Clone este repositório:
```bash
git clone [https://github.com/HerickGIS/dossie-mapas-mestrado.git](https://github.com/HerickGIS/dossie-mapas-mestrado.git)
