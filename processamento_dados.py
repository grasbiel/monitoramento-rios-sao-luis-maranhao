import pandas as pd
import numpy as np
import re
import os
import unicodedata
from sklearn.neighbors import KNeighborsClassifier

# ==============================================================================
# 1. CONFIGURAÇÕES
# ==============================================================================
CAMINHO_ENTRADA = "data/raw/dados_brutos.xlsx"
CAMINHO_SAIDA = "data/processed/dados_tratados_tcc.csv"

# Limites "Grosseiros" de São Luís (Para forçar a escala correta)
# Se a coordenada não estiver aqui, vamos dividir por 10 até entrar.
CHECK_LAT_MIN, CHECK_LAT_MAX = -4.0, -1.0
CHECK_LON_MIN, CHECK_LON_MAX = -46.0, -42.0

# Limites "Finos" (Geofencing final - Seu corte original)
FINAL_LAT_MIN, FINAL_LAT_MAX = -2.80, -2.30
FINAL_LON_MIN, FINAL_LON_MAX = -44.50, -44.00

# ==============================================================================
# 2. FUNÇÕES INTELIGENTES
# ==============================================================================

def padronizar_texto(texto):
    """Remove acentos, espaços e joga pra maiúsculo."""
    if pd.isna(texto): return texto
    texto = str(texto).upper().strip()
    return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')

def limpar_coordenada_inteligente(valor, tipo='lat'):
    """
    Função Auto-Corretiva: Divide o valor por 10 sucessivamente até ele
    fazer sentido geográfico para o Maranhão.
    """
    if pd.isna(valor): return np.nan
    
    # 1. Limpeza de caracteres (tira letras, mantem numeros, ponto e menos)
    valor_str = str(valor).strip().replace(',', '.')
    valor_limpo = re.sub(r'[^0-9\.\-]', '', valor_str)
    
    try:
        coord = float(valor_limpo)
    except ValueError:
        return np.nan

    # 2. Garante sinal negativo (Estamos no Hemisfério Sul / Oeste)
    if coord > 0: coord = -coord
    
    # 3. Correção de Escala (Loop de divisão)
    # Se for Latitude, tem que estar entre -1 e -4. Se for -2500, divide até chegar lá.
    if tipo == 'lat':
        # Evita loop infinito: para se ficar menor que 0.1 (zero absoluto)
        while abs(coord) > 4.0 and abs(coord) > 0.1: 
            coord = coord / 10.0
        
        # Validação final: Está em São Luís?
        if not (CHECK_LAT_MIN < coord < CHECK_LAT_MAX):
            return np.nan # Dado irrecuperável
            
    elif tipo == 'lon':
        while abs(coord) > 46.0 and abs(coord) > 0.1:
            coord = coord / 10.0
            
        if not (CHECK_LON_MIN < coord < CHECK_LON_MAX):
            return np.nan

    return coord

def classificar_conama(row):
    problemas = []
    # Usando 0 como placeholder de "Sem dado" (não reprova por falta de dado)
    if row['ph'] != 0 and not (6.0 <= row['ph'] <= 9.0): problemas.append('pH')
    if row['od'] != 0 and row['od'] < 5.0: problemas.append('OD')
    if row['turbidez'] != 0 and row['turbidez'] > 100.0: problemas.append('Turbidez')
    
    return len(problemas), ", ".join(problemas)

# ==============================================================================
# 3. PIPELINE DE EXECUÇÃO
# ==============================================================================

def executar_etl():
    print("--- INICIANDO PROCESSAMENTO (MODO CORREÇÃO) ---")

    # A. Carregar
    if not os.path.exists(CAMINHO_ENTRADA):
        print(f"🚨 ERRO: Arquivo não encontrado: {CAMINHO_ENTRADA}")
        return
    df_bruto = pd.read_excel(CAMINHO_ENTRADA)

    # B. Renomear (VOLTAMOS AO MAPEAMENTO ORIGINAL DO COLAB)
    mapa_colunas = {
        "Nome Municipio": "municipio",
        "Nome do Corpo D'Água": "rio",
        "Data da Coleta (dd/mm/aaaa)": "data",
        "Posição horizontal da coleta (latitude)": "latitude",  # Voltei ao original
        "Posição vertical da coleta (longitude)": "longitude", # Voltei ao original
        # Variáveis
        "pH": "ph", "Oxigênio dissolvido (mg/L 02)": "od", "Turbidez (NTU)": "turbidez",
        "Temperatura da água (°C)": "temperatura",
        "Condutividade Elétrica Específica (25°C) (µS/cm a 25°C)": "condutividade",
        "Sólidos Dissolvidos (mg/L)": "std",
        "Fósforo Total\n (mg/L de P)": "fosforo",
        "Nitrogênio Amoniacal\n (mg/L de N)": "nitrogenio",
        "Salinidade (‰)": "salinidade"
    }
    cols = [c for c in mapa_colunas.keys() if c in df_bruto.columns]
    df = df_bruto[cols].rename(columns=mapa_colunas)

    # C. Datas (Correção do 30/28/2018)
    print("Tratando datas...")
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df = df.dropna(subset=['data'])

    # D. Padronização
    if 'municipio' in df.columns: df['municipio'] = df['municipio'].apply(padronizar_texto)
    if 'rio' in df.columns: df['rio'] = df['rio'].apply(padronizar_texto)
    
    # Filtro Municipio
    df = df[df['municipio'] == 'SAO LUIS'].copy()
    if df.empty:
        print("🚨 ERRO CRÍTICO: Filtro 'SAO LUIS' removeu tudo. Verifique o nome no Excel.")
        return

    # E. Limpeza de Coordenadas (COM DEBUG)
    print("\n--- AMOSTRA DE COORDENADAS ANTES DA LIMPEZA ---")
    print(df[['latitude', 'longitude']].head(3).to_string())

    df['latitude'] = df['latitude'].apply(lambda x: limpar_coordenada_inteligente(x, 'lat'))
    df['longitude'] = df['longitude'].apply(lambda x: limpar_coordenada_inteligente(x, 'lon'))
    
    # Remove inválidos
    df = df.dropna(subset=['latitude', 'longitude'])

    print("\n--- AMOSTRA DE COORDENADAS DEPOIS DA LIMPEZA ---")
    print(df[['latitude', 'longitude']].head(3).to_string())
    print("------------------------------------------------\n")

    # F. Geofencing (Corte Fino)
    df_geo = df[
        (df['latitude'].between(FINAL_LAT_MIN, FINAL_LAT_MAX)) & 
        (df['longitude'].between(FINAL_LON_MIN, FINAL_LON_MAX))
    ].copy()
    
    print(f"Registros válidos após Geofencing: {len(df_geo)} (de {len(df)} originais)")

    # G. KNN Rios (Mantido)
    print("Processando nomes de rios...")
    df_treino = df_geo.dropna(subset=['rio']).copy()
    mask_nulos = df_geo['rio'].isna() | (df_geo['rio'] == '')
    
    if not df_treino.empty and mask_nulos.sum() > 0:
        knn = KNeighborsClassifier(n_neighbors=1)
        knn.fit(df_treino[['latitude', 'longitude']].values, df_treino['rio'].values)
        df_geo.loc[mask_nulos, 'rio'] = knn.predict(df_geo.loc[mask_nulos, ['latitude', 'longitude']].values)

    # H. Tratamento Numérico (Zerando vazios)
    cols_num = ['ph', 'od', 'turbidez', 'temperatura', 'condutividade', 'fosforo']
    for col in cols_num:
        if col in df_geo.columns:
            df_geo[col] = pd.to_numeric(df_geo[col], errors='coerce').fillna(0.0)

    # I. Classificação
    classificacao = df_geo.apply(classificar_conama, axis=1, result_type='expand')
    df_geo['indice_problemas'] = classificacao[0]
    df_geo['lista_problemas'] = classificacao[1]
    df_geo['resultado_final'] = df_geo['indice_problemas'].apply(lambda x: 'Aprovado' if x == 0 else 'Reprovado')

    # Status individuais
    df_geo['status_ph'] = df_geo['ph'].apply(lambda x: 'Fora' if (x>0 and not 6<=x<=9) else 'OK')
    df_geo['status_od'] = df_geo['od'].apply(lambda x: 'Fora' if (x!=0 and x<5) else 'OK')
    
    # Salvar
    os.makedirs(os.path.dirname(CAMINHO_SAIDA), exist_ok=True)
    df_geo.to_csv(CAMINHO_SAIDA, index=False)
    print(f"✅ SUCESSO! Arquivo salvo: {CAMINHO_SAIDA}")

if __name__ == "__main__":
    executar_etl()