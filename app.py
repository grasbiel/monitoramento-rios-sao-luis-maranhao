import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

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

tab1, tab2, tab3 = st.tabs([
    "Conformidade por Parâmetro", 
    "Evolução Temporal (OD)",
    "Estatística Científica"
    ])

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
    
    config_parametros = {
        "Oxigênio Dissolvido (OD)": {
            "col": "od", "cor": "blue", "limite": 5.0, "tipo_lim": "min", "ylabel": "mg/L"
        },
        "Turbidez": {
            "col": "turbidez", "cor": "brown", "limite": 100.0, "tipo_lim": "max", "ylabel": "NTU"
        },
        "pH": {
            "col": "ph", "cor": "green", "limite": [6.0, 9.0], "tipo_lim": "range", "ylabel": "pH"
        },
        "Temperatura": {
            "col": "temperatura", "cor": "orange", "limite": None, "tipo_lim": "none", "ylabel": "°C"
        },
        "Salinidade": {
            "col": "salinidade", "cor": "purple", "limite": None, "tipo_lim": "none", "ylabel": "ppt"
        },
        "Condutividade": {
            "col": "condutividade", "cor": "teal", "limite": None, "tipo_lim": "none", "ylabel": "µS/cm"
        },
        "Sólidos Totais (STD)": {
            "col": "std", "cor": "gray", "limite": 500.0, "tipo_lim": "max", "ylabel": "mg/L"
        },
        "Nitrogênio Total": {
            "col": "nitrogenio", "cor": "magenta", "limite": 2.18, "tipo_lim": "max", "ylabel": "mg/L"
        },
        "Fósforo Total": {
            "col": "fosforo", "cor": "red", "limite": 0.1, "tipo_lim": "max", "ylabel": "mg/L"
        }
    }
    
    # 2. Seletor de Parâmetro (Usa as chaves do dicionário)
    parametro_selecionado = st.selectbox(
        "Selecione o Indicador para visualizar:",
        list(config_parametros.keys())
    )
    
    # Recupera as configurações da escolha
    cfg = config_parametros[parametro_selecionado]
    coluna = cfg['col']
    
    # 3. Verificação e Plotagem
    if not df_filtrado.empty and coluna in df_filtrado.columns:
        
        # Agrupa por mês para suavizar (Média Mensal)
        # 'ME' é o alias novo do pandas para Month End (antigo 'M')
        df_temp = df_filtrado.set_index('data').resample('ME')[coluna].mean().reset_index()

        # Verifica se há dados válidos após o resample
        if df_temp[coluna].notna().sum() > 0:
            
            fig2, ax = plt.subplots(figsize=(12, 5))
            
            # Plota a linha de tendência
            sns.lineplot(
                data=df_temp, x='data', y=coluna, 
                marker='o', color=cfg['cor'], linewidth=2, label='Média Mensal'
            )

            # --- Lógica das Linhas de Limite (CONAMA) ---
            if cfg['tipo_lim'] == 'min':
                lim = cfg['limite']
                plt.axhline(lim, color='red', linestyle='--', label=f'Mínimo ({lim})')
                plt.fill_between(df_temp['data'], 0, lim, color='red', alpha=0.1)

            elif cfg['tipo_lim'] == 'max':
                lim = cfg['limite']
                plt.axhline(lim, color='red', linestyle='--', label=f'Máximo ({lim})')
                # Teto visual dinâmico
                max_y = df_temp[coluna].max()
                teto = max(max_y, lim) * 1.2 if pd.notna(max_y) else lim * 1.2
                plt.fill_between(df_temp['data'], lim, teto, color='red', alpha=0.1)

            elif cfg['tipo_lim'] == 'range':
                lim_min, lim_max = cfg['limite']
                plt.axhline(lim_min, color='red', linestyle='--', label=f'Min ({lim_min})')
                plt.axhline(lim_max, color='red', linestyle='--', label=f'Max ({lim_max})')
                plt.fill_between(df_temp['data'], 0, lim_min, color='red', alpha=0.1)
                
                # Definindo teto para o gráfico de pH
                plt.fill_between(df_temp['data'], lim_max, 14, color='red', alpha=0.1)
                plt.ylim(4, 10) 

            # Configurações Finais do Gráfico
            plt.title(f"Evolução Temporal: {parametro_selecionado}")
            plt.ylabel(cfg['ylabel'])
            plt.xlabel("Data")
            plt.legend()
            plt.grid(True, linestyle=':', alpha=0.6)
            
            st.pyplot(fig2)
    else:
        st.warning("Sem dados suficientes para gerar o gráfico temporal com os filtros atuais.")

with tab3:
    st.markdown("### Análise de Correlação e Disponibilidade de Dados")
    st.markdown("""
                *Esta seção visa atender ao rigor científico, analisando a matriz de correção físico-químicos e identificando a consistência do monitoramento
                """)
    
    if not df_filtrado.empty:
        cols_analise = [
            "ph", "od", "turbidez", "temperatura", "condutividade", "std","nitrogenio","salinidade","fosforo"
        ]
        
        df_cientifico = df_filtrado[cols_analise].copy()
        
        df_cientifico = df_cientifico.replace(0.0, float('nan'))
        
        col_c1, col_c2 = st.columns([1,1])
        
        # Análise de dados faltantes
        with col_c1:
            st.markdown("Consistência do Monitoramento")
            st.caption("Percentual de amostras com dados válidos (não nulos) no período selecionado")
            
            # Cálculo de porcentagem de preenchimento
            total = len(df_cientifico)
            preenchimento = (df_cientifico.count() / total) * 100
            df_missing = pd.DataFrame(preenchimento, columns=['% Preenchimento']).sort_values('% Preenchimento', ascending=True)
            
            fig_miss, ax_miss = plt.subplots(figsize=(6,6))
            sns.barplot(x=df_missing['% Preenchimento'], y= df_missing.index, ax= ax_miss, palette="viridis", hue=df_missing.index)
            ax_miss.set_xlabel("% de Dados Disponíveis")
            ax_miss.set_xlim(0,100)
            ax_miss.grid(axis="x", linestyle="--", alpha=0.5)
            
            for i, v in enumerate(df_missing["% Preenchimento"]):
                ax_miss.text(v + 1, i, f"{v:.1f}", va="center", fontsize=9)
            
            st.pyplot(fig_miss)
            
        # Matriz de Correlação (Pearson)            
        with col_c2:
            st.markdown("Matriz de Correlação (Pearson)")
            st.caption("Indica como as variáevis interagem. (1= Correlação Positiva Perfeita, -1 = Negativa Perfeita)")
            
            corr = df_cientifico.corr()
            
            fig_corr, ax_corr = plt.subplots(figsize=(8,8))
            mask = np.triu(np.ones_like(corr, dtype=bool))
            
            sns.heatmap(corr, mask=mask, cmap="coolwarm", vmin=1, vmax=1, center=0,
                        annot=True, fmt=".2f", square=True, linewidths=.5, cbar_kws={"shrink": .5})
            
            plt.xticks(rotation=45, ha="right")
            st.pyplot(fig_corr)
            
        
        # Insights
        st.divider()
        st.markdown("**💡 Insights Automáticos (Baseado nos dados filtrados):**")
        
        cor_od_turb = corr.loc['temperatura', 'ph']
        texto_corr = "fraca"
        if abs(cor_od_turb) > 0.5: texto_corr = "moderada"
        if abs(cor_od_turb) > 0.7: texto_corr = "forte"
        tipo_corr = "negativa (inversa)" if cor_od_turb < 0 else "positiva (direta)"
        
        st.write(f"A correlação entre **OD e Turbidez** é **{texto_corr} e {tipo_corr}** ({cor_od_turb:.2f}).")
    
    else:
        st.warning("Sem dados suficientes para análise estatística")
        