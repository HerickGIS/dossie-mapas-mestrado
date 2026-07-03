import sidrapy
import pandas as pd

print("Baixando dados do SIDRA...")
# População Censo 2022 para todos os municípios do RN (24) e PB (25)
df = sidrapy.get_table(table_code="4714", territorial_level="6", ibge_territorial_code="24*,25*")
df.columns = df.iloc[0]
df = df[1:]

# Seleciona só o que importa
df = df[['Município', 'Valor']]
df.rename(columns={'Valor': 'POP_2022'}, inplace=True)
df.to_csv("data/dados_ibge_populacao.csv", index=False)
print("✅ Dados salvos em data/dados_ibge_populacao.csv com sucesso!")
