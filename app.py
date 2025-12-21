import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

st.set_page_config(
    page_title="Monitoramento Hídrico - São Luís-MA",
    page_icon="💧",
    layout="wide"
)

st.title(" 💧 Painel de Monitoramento da Qualidade da Água - São Luís-MA")
st.markdown(
    """
    **Objeto do estudo:** Corpos hídricos da Ilha de São Luís/MA.
    **Metodologia:** Tratamento de dados via Python e Classificação conforme **Resolução CONAMA 357/2005**.
    """
)

st.markdown("----")

@st.cache_data
def carregar_dados():
    try: 
        df= pd.read_csv("data/processed/dados_tratados_tcc.csv")
        df['data']=pd.to_datetime(df['data'], format="mixed", errors='coerce', dayfirst=True)
        return df   
    except FileNotFoundError:
        return None
df_raw = carregar_dados()

if df_raw is None:  
    st.error("Erro: O arquivo de dados não foi encontrado. Por favor, verifique o caminho do arquivo e tente novamente.")
    st.info("Por favor, exporte o dataframe final do seu código Python e coloque na mesma pasta deste arquivo app.py.")
    st.stop()

# Filtros

df_raw['ano_filtro'] = df_raw['data'].dt.year.astype(int)


st.sidebar.header("Filtros de Análise")

# Filtro do ano
anos_disponiveis= sorted(df_raw['ano_filtro'].unique(), reverse = True)
anos_selecionados= st.sidebar.multiselect("Selecione os anos:", anos_disponiveis, default= anos_disponiveis)

# Filtro de rio
rios_disponiveis = sorted(df_raw['rio'].unique())
rios_selecionados = st.sidebar.multiselect("Selecione os rios:", rios_disponiveis, default= rios_disponiveis)

# Aplicação de filtros
df_filtrado = df_raw[
    (df_raw['ano_filtro'].isin(anos_selecionados)) &
    (df_raw['rio'].isin(rios_selecionados))
]


# Indicadores principais

col1, col2, col3, col4 = st.columns(4)

total_amostras = len(df_filtrado)


if total_amostras > 0:
    # Cálculo de aprovação: Se indice_problemas == 0, então aprovado
    qtd_aprovados = len(df_filtrado[df_filtrado['indice_problemas'] == 0])
    percentual_aprovados = (qtd_aprovados/total_amostras) * 100

    df_problemas = df_filtrado[df_filtrado['indice_problemas'] > 0]
    if not df_problemas.empty:
        rio_critico_nome = df_problemas['rio'].mode()[0]
    else:
        rio_critico_nome= "Nenhum"

else:
    percentual_aprovados = 0
    rio_critico_nome = "-"

col1.metric("Amostras analisadas", total_amostras)
col2.metric("Índice de conformidade", f"{percentual_aprovados:.2f} %")
col3.metric("Rio mais crítico", rio_critico_nome)
col4.metric("Parâmetros vilão", "Oxigênio Dissolvido", delta="Alerta Ambiental", delta_color="inverse")


st.subheader("Mapa de Vulnerabilidade Hídrica")

if not df_filtrado.empty:
    centro = [df_filtrado['latitude'].mean(), df_filtrado['longitude'].mean()]
    m = folium.Map(location=centro, zoom_start=11, tiles='CartoDB positron')
    marker_cluster = MarkerCluster().add_to(m)

    def cor_status(n_problemas):
        if n_problemas == 0: return 'green'   # Tudo certo
        if n_problemas == 1: return 'orange'  # Atenção
        return 'red'                          # Crítico (2 ou mais problemas)

    for _, row in df_filtrado.iterrows():
        # Lógica do Status Texto
        status_texto = "CONFORME" if row['indice_problemas'] == 0 else "NÃO CONFORME"
        cor_texto = "green" if row['indice_problemas'] == 0 else "red"
        
        # HTML do Popup
        html = f"""
        <div style="font-family: sans-serif; font-size: 12px; width:220px">
            <b>Rio:</b> {row['rio']}<br>
            <b>Data:</b> {row['data'].strftime('%d/%m/%Y')}<br>
            <hr>
            <b>Status Geral:</b> <span style="color:{cor_texto}; font-weight:bold;">{status_texto}</span><br>
            (Problemas identificados: {row['indice_problemas']})<br>
            <br>
            <b>pH:</b> {row['ph']} <span style="color:gray; font-size:10px">({row['status_ph']})</span><br>
            <b>OD:</b> {row['od']} mg/L <span style="color:gray; font-size:10px">({row['status_od']})</span><br>
            <b>Turbidez:</b> {row['turbidez']} NTU <span style="color:gray; font-size:10px">({row['status_turbidez']})</span>
        </div>
        """
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(html, max_width=250),
            icon=folium.Icon(color=cor_status(row['indice_problemas']), icon='info-sign')
        ).add_to(marker_cluster)

    st_folium(m, width=None, height=500)
else:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")

st.subheader("📊 Diagnóstico Visual")

tab1, tab2 = st.tabs(["Conformidade por Parâmetro", "Evolução Temporal (OD)"])

with tab1:
    if not df_filtrado.empty:
        col_g1, col_g2, col_g3 = st.columns(3)
        
        # Função para plotar, usando as colunas 'status_ph', 'status_od', etc.
        def plotar_barra(coluna_status, titulo, local_plot):
            if coluna_status in df_filtrado.columns:
                fig, ax = plt.subplots(figsize=(5,4))
                
                # Conta os valores
                contagem = df_filtrado[coluna_status].value_counts()
                
                # Define cores (ajuste as chaves conforme o texto exato do seu CSV)
                # Exemplo: Se no CSV estiver "Dentro do Padrão" e "Fora do Padrão"
                paleta_cores = {
                    'Dentro do Padrão': '#2ecc71', # Verde
                    'Fora do Padrão': '#e74c3c',   # Vermelho
                    'Sem Dado': '#95a5a6',          # Cinza
                    # Adicione variações se necessário, ex: "Conforme", "Não Conforme"
                    'Conforme': '#2ecc71',
                    'Não Conforme': '#e74c3c'
                }
                
                sns.barplot(x=contagem.index, y=contagem.values, ax=ax, palette=paleta_cores, hue = contagem.index)
                ax.set_title(titulo)
                ax.set_ylabel("Qtd. Amostras")
                ax.set_xlabel("")
                
                # Rótulos nas barras
                for p in ax.patches:
                    if p.get_height() > 0:
                        ax.annotate(f'{int(p.get_height())}', 
                                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                                    ha='center', va='bottom')
                                    
                local_plot.pyplot(fig)
            else:
                local_plot.warning(f"Coluna {coluna_status} não encontrada.")
        
        with col_g1: plotar_barra('status_ph', 'pH', st)
        with col_g2: plotar_barra('status_od', 'Oxigênio (OD)', st)
        with col_g3: plotar_barra('status_turbidez', 'Turbidez', st)


with tab2:
    st.markdown("Analise a tendência dos parâmetros ao longo do tempo.")
    
    # 1. Seletor de Parâmetro
    parametro = st.selectbox(
        "Selecione o Indicador para visualizar:",
        ["Oxigênio Dissolvido (OD)", "Turbidez", "pH"]
    )

    # 2. Configuração Dinâmica (O que muda para cada escolha)
    if parametro == "Oxigênio Dissolvido (OD)":
        coluna = 'od'
        cor_linha = 'blue'
        limite_val = 5.0
        tipo_limite = 'min' # Deve ser MAIOR que isso
        ylabel = 'Concentração (mg/L)'
    
    elif parametro == "Turbidez":
        coluna = 'turbidez'
        cor_linha = 'brown'
        limite_val = 100.0
        tipo_limite = 'max' # Deve ser MENOR que isso
        ylabel = 'Turbidez (NTU)'
    
    else: # pH
        coluna = 'ph'
        cor_linha = 'green'
        limite_val = [6.0, 9.0] # Faixa
        tipo_limite = 'range'
        ylabel = 'pH'

    # 3. Gerando o Gráfico
    if not df_filtrado.empty:
        # Agrupa por mês para suavizar o gráfico
        df_temp = df_filtrado.set_index('data').resample('ME')[coluna].mean().reset_index()
        
        fig2, ax = plt.subplots(figsize=(12, 5))
        
        # Plota a linha de tendência
        sns.lineplot(data=df_temp, x='data', y=coluna, marker='o', color=cor_linha, linewidth=2, label='Média Mensal')
        
        # Lógica das Linhas de Limite (CONAMA)
        if tipo_limite == 'min':
            plt.axhline(limite_val, color='red', linestyle='--', label=f'Mínimo ({limite_val})')
            # Pinta a área ruim (abaixo da linha)
            plt.fill_between(df_temp['data'], 0, limite_val, color='red', alpha=0.1)
            
        elif tipo_limite == 'max':
            plt.axhline(limite_val, color='red', linestyle='--', label=f'Máximo ({limite_val})')
            # Pinta a área ruim (acima da linha)
            # Definindo um teto visual razoável para o fill_between
            max_y = df_temp[coluna].max()
            plt.fill_between(df_temp['data'], limite_val, max(max_y, limite_val)*1.2, color='red', alpha=0.1)
            
        elif tipo_limite == 'range':
            plt.axhline(limite_val[0], color='red', linestyle='--', label='Min (6.0)')
            plt.axhline(limite_val[1], color='red', linestyle='--', label='Max (9.0)')
            # Pinta as áreas ruins
            plt.fill_between(df_temp['data'], 0, limite_val[0], color='red', alpha=0.1)
            plt.fill_between(df_temp['data'], limite_val[1], 14, color='red', alpha=0.1)
            plt.ylim(4, 10) # Foco visual no pH

        plt.title(f"Evolução Temporal: {parametro}")
        plt.ylabel(ylabel)
        plt.xlabel("Data")
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.6)
        
        st.pyplot(fig2)
    else:
        st.warning("Sem dados suficientes para gerar o gráfico temporal com os filtros atuais.")
