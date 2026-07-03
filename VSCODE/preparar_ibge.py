import geopandas as gpd
import geobr
import pandas as pd

print("1. Conectando aos servidores do IBGE para baixar os Setores Censitários (2022)...")
# Como a Bacia do Rio do Carmo abrange o RN e uma pontinha da Paraíba, baixamos ambos
setores_rn = geobr.read_census_tract(code_tract="RN", year=2022)
setores_pb = geobr.read_census_tract(code_tract="PB", year=2022)

# Junta os dois estados em um mapa só
setores_total = pd.concat([setores_rn, setores_pb], ignore_index=True)

print("2. Carregando o seu mapa de Vulnerabilidade Ambiental...")
# Ajuste o caminho se o nome do seu arquivo original for diferente
bacia_vuln = gpd.read_file("data/dados_ppgeo_bh_vulnerabilidade_ambiental.geojson")

print("3. Alinhando as projeções cartográficas para cálculo (SIRGAS 2000 UTM 24S)...")
setores_total = setores_total.to_crs(epsg=31984)
bacia_vuln = bacia_vuln.to_crs(epsg=31984)

print("4. Realizando o Cruzamento Espacial (Spatial Join)...")
# A MÁGICA: Recorta o IBGE usando o limite da sua bacia e herda a coluna "CLASSE" da Ecodinâmica
setores_bacia = gpd.sjoin(setores_total, bacia_vuln, how="inner", predicate="intersects")

print("5. Salvando o arquivo otimizado para a Web...")
# Volta para WGS84 (Padrão da Internet) e salva o GeoJSON limpo
setores_bacia = setores_bacia.to_crs(epsg=4326)
setores_bacia.to_file("data/dados_ibge_cruzamento_carmo.geojson", driver="GeoJSON")

print("✅ Sucesso! O arquivo 'dados_ibge_cruzamento_carmo.geojson' foi criado na sua pasta data.")
