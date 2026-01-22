import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import numpy as np
import plotly.express as px

# --- Configuração da Página ---
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

# Carregamento de Dados
@st.cache_data
def carregar_dados():
    try: 
        df = pd.read_csv("data/processed/dados_tratados_tcc.csv")
        # Força a conversão de datas garantindo compatibilidade
        df['data'] = pd.to_datetime(df['data'], format="mixed", errors='coerce', dayfirst=True)
        # Garante que valores nulos nas colunas de status sejam 'Sem Dado' para evitar erros no gráfico
        cols_status = ['status_ph', 'status_od', 'status_turbidez']
        for col in cols_status:
            if col in df.columns:
                df[col] = df[col].fillna('Sem Dado')
        return df   
    except FileNotFoundError:
        return None

df_raw = carregar_dados()

if df_raw is None:  
    st.error("Erro: O arquivo de dados não foi encontrado. Por favor, verifique o caminho do arquivo e tente novamente.")
    st.info("Por favor, exporte o dataframe final do seu código Python e coloque na mesma pasta deste arquivo app.py.")
    st.stop()

# Diagnóstico de amostras
def exibir_estatisticas_amostragem(df):
    
    if df.empty:
        return

    st.markdown("### 📊 Matriz de Diagnóstico por Bacia Hidrográfica")
    st.caption("Médias dos principais indicadores de qualidade (Baseado na literatura de Hidroinformática)")
    
    # 1. Agrupamento Inteligente
    stats = df.groupby('rio').agg(
        Qtd=('rio', 'count'),
        OD_Medio=('od', 'mean'),
        Turb_Media=('turbidez', 'mean'),
        pH_Medio=('ph', 'mean')
    ).reset_index()
    
    # Cálculo de percentual
    total = stats['Qtd'].sum()
    if total > 0:
        stats['Freq (%)'] = (stats['Qtd'] / total) * 100
    else:
        stats['Freq (%)'] = 0
    
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.markdown("**Volume de Monitoramento**")
        fig = px.bar(
            stats.sort_values(by="Qtd", ascending=True),
            x='Qtd',
            y='rio',
            orientation='h',
            text='Qtd',
            color='Qtd',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            showlegend=False, 
            height=300, 
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis_title=None,
            yaxis_title=None
        )
        st.plotly_chart(fig, width="stretch")
        
    with c2:
        st.markdown("**Indicadores Médios do Período**")
        st.dataframe(
            stats,
            column_config={
                "rio": "Bacia Hidrográfica",
                "Qtd": st.column_config.NumberColumn("Amostras", format="%d"),
                "Freq (%)": st.column_config.ProgressColumn("Part. %", format="%.1f%%", min_value=0, max_value=100),
                "OD_Medio": st.column_config.NumberColumn("OD (mg/L)", format="%.2f", help="Média de Oxigênio Dissolvido. Ideal > 5.0"),
                "Turb_Media": st.column_config.NumberColumn("Turbidez (NTU)", format="%.1f", help="Média de Turbidez. Ideal < 100"),
                "pH_Medio": st.column_config.NumberColumn("pH", format="%.1f", help="Faixa ideal: 6.0 a 9.0"),
            },
            hide_index=True,
            width="stretch"
        )
    st.markdown("---")


# ==============================================================================


# --- Filtros ---
df_raw['ano_filtro'] = df_raw['data'].dt.year.astype(int)

st.sidebar.header("Filtros de Análise")

# Filtro do ano
anos_disponiveis = sorted(df_raw['ano_filtro'].unique(), reverse=True)
anos_selecionados = st.sidebar.multiselect("Selecione os anos:", anos_disponiveis, default=anos_disponiveis)

# Filtro de rio
rios_disponiveis = sorted(df_raw['rio'].unique())
rios_selecionados = st.sidebar.multiselect("Selecione os rios:", rios_disponiveis, default=rios_disponiveis)

# Aplicação de filtros
df_filtrado = df_raw[
    (df_raw['ano_filtro'].isin(anos_selecionados)) &
    (df_raw['rio'].isin(rios_selecionados))
]

# --- Indicadores principais (KPIs) ---
col1, col2, col3, col4 = st.columns(4)

total_amostras = len(df_filtrado)

if total_amostras > 0:
    qtd_aprovados = len(df_filtrado[df_filtrado['indice_problemas'] == 0])
    percentual_aprovados = (qtd_aprovados/total_amostras) * 100

    # Cálculo do rio mais crítico (Dinâmico)
    # Filtra apenas linhas com problemas (>0)
    df_problemas = df_filtrado[df_filtrado['indice_problemas'] > 0]
    
    if not df_problemas.empty:
        rio_critico_nome = df_problemas['rio'].mode()[0]
    else:
        rio_critico_nome = "Nenhum"
        
    mapa_colunas_status = {
        'stadus_od': 'Oxigênio Dissolvido',
        'status_turbidez': 'Turbidez',
        'status_ph': 'pH'
    }
    
    contagem_erros = {}
    
    for col_db, nome_exibicao in mapa_colunas_status.items():
        if col_db in df_filtrado.columns:
            erros = df_filtrado[col_db].isin(['Não Conforme', 'Fora do Padrão', 'Ruim', 'Péssimo']).sum()
            contagem_erros[nome_exibicao] = erros
            
    if contagem_erros:
        vilao_nome = max(contagem_erros, key = contagem_erros.get)
        qtd_erros_vilao = contagem_erros[vilao_nome]
        
        if qtd_erros_vilao == 0:
            vilao_nome = "Nenhum"
            
    else:
        vilao_nome = "-"
else:
    percentual_aprovados = 0
    rio_critico_nome = "-"
    vilao_nome= "-"

col1.metric("Amostras analisadas", total_amostras)
col2.metric("Índice de conformidade", f"{percentual_aprovados:.2f} %")
col3.metric("Rio mais crítico", rio_critico_nome, help="Rio com maior frequência de não-conformidades na seleção atual")
col4.metric("Parâmetro vilão", vilao_nome, delta="Maior causa de reprovação", delta_color="inverse", help= "Parâmetro que mais falhou no período/local selecionado.")


exibir_estatisticas_amostragem(df_filtrado)


# Mapa 
st.subheader("Mapa de Vulnerabilidade Hídrica")

if not df_filtrado.empty:
    
    if 'reset_mapa_id' not in st.session_state:
        st.session_state.reset_mapa_id = 0

    col_msg, col_btn = st.columns([0.8, 0.2])
    with col_msg:
        st.caption("Visualize os pontos de coleta no mapa.")
    with col_btn:
        if st.button("🎯 Centralizar"):
            st.session_state.reset_mapa_id += 1

    centro_padrao = [-2.5307, -44.3068]
    
    m = folium.Map(location=centro_padrao, zoom_start=11, tiles='CartoDB positron')
    marker_cluster = MarkerCluster().add_to(m)

    def cor_status(n_problemas):
        if n_problemas == 0: return 'green'
        if n_problemas == 1: return 'orange'
        return 'red'

    for _, row in df_filtrado.iterrows():
        status_texto = "CONFORME" if row['indice_problemas'] == 0 else "NÃO CONFORME"
        cor_texto = "green" if row['indice_problemas'] == 0 else "red"
        
        html = f"""
        <div style="font-family: sans-serif; font-size: 12px; width:200px">
            <b>Rio:</b> {row['rio']}<br>
            <b>Data:</b> {row['data'].strftime('%d/%m/%Y')}<br>
            <hr>
            <b>Status:</b> <span style="color:{cor_texto}">{status_texto}</span>
            (Prob: {row['indice_problemas']})<br>
            OD: {row['od']} | Turb: {row['turbidez']} | pH: {row['ph']}
        </div>
        """
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(html, max_width=250),
            icon=folium.Icon(color=cor_status(row['indice_problemas']), icon='info-sign')
        ).add_to(marker_cluster)

    st_folium(
        m, 
        width=None, 
        height=500, 
        key=f"mapa_monitoramento_{st.session_state.reset_mapa_id}"
    )

else:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    
    
# Abas de Diagnóstico
st.subheader("📊 Diagnóstico Visual")

tab1, tab2, tab3 = st.tabs([
    "Conformidade por Parâmetro", 
    "Evolução Temporal (OD)",
    "Estatística Científica"
    ])

with tab1:
    if not df_filtrado.empty:
        col_g1, col_g2, col_g3 = st.columns(3)
        
        def plotar_barra(coluna_status, titulo, local_plot):
            if coluna_status in df_filtrado.columns:
                fig, ax = plt.subplots(figsize=(5,4))
                
                # Preenche vazios com 'Sem Dado' para evitar erro
                series_plot = df_filtrado[coluna_status].fillna('Sem Dado')
                contagem = series_plot.value_counts()
                
                
                
                paleta_cores = {
                    'Dentro do Padrão': '#2ecc71', # Verde
                    'Fora do Padrão': '#e74c3c',   # Vermelho
                    'Conforme': '#2ecc71',
                    'Não Conforme': '#e74c3c',
                    'Sem Dado': '#95a5a6',         # Cinza
                    'Sem dado': '#95a5a6'          # Cinza
                }
                
                sns.barplot(x=contagem.index, y=contagem.values, ax=ax, palette=paleta_cores, hue=contagem.index)
                ax.set_title(titulo)
                ax.set_ylabel("Qtd. Amostras")
                ax.set_xlabel("")
                
                for p in ax.patches:
                    if p.get_height() > 0:
                        ax.annotate(f'{int(p.get_height())}', 
                                    (p.get_x() + p.get_width() / 2., p.get_height()), 
                                    ha='center', va='bottom')
                                    
                local_plot.pyplot(fig)
            else:
                local_plot.info(f"Dados de {titulo} indisponíveis para este gráfico.")
        
        with col_g1: plotar_barra('status_ph', 'pH', st)
        with col_g2: plotar_barra('status_od', 'Oxigênio (OD)', st)
        with col_g3: plotar_barra('status_turbidez', 'Turbidez', st)


with tab2:
    st.markdown("### Análise de Tendências Temporais")

    config_parametros = {
        "Oxigênio Dissolvido (OD)": {
            "col": "od", "cor": "blue", "limite": 5.0, "tipo_lim": "min", "ylabel": "Concentração (mg/L)"
        },
        "Turbidez": {
            "col": "turbidez", "cor": "brown", "limite": 100.0, "tipo_lim": "max", "ylabel": "Turbidez (NTU)"
        },
        "pH": {
            "col": "ph", "cor": "green", "limite": [6.0, 9.0], "tipo_lim": "range", "ylabel": "pH"
        },
        "Temperatura Água": {
            "col": "temperatura_agua", "cor": "orange", "limite": None, "tipo_lim": "none", "ylabel": "Temperatura (°C)"
        },
        "Salinidade": {
            "col": "salinidade", "cor": "purple", "limite": None, "tipo_lim": "none", "ylabel": "Salinidade (ppt)"
        },
        "Condutividade": {
            "col": "condutividade", "cor": "teal", "limite": None, "tipo_lim": "none", "ylabel": "Condutividade (µS/cm)"
        },
        "Sólidos Totais (STD)": {
            "col": "solidos_dissolvidos", "cor": "gray", "limite": 500.0, "tipo_lim": "max", "ylabel": "Sólidos Totais (mg/L)"
        },
        "Nitrogênio Total": {
            "col": "nitrogenio", "cor": "magenta", "limite": 2.18, "tipo_lim": "max", "ylabel": "Nitrogênio (mg/L)"
        },
        "Fósforo Total": {
            "col": "fosforo", "cor": "red", "limite": 0.1, "tipo_lim": "max", "ylabel": "Fósforo (mg/L)"
        }
    }

    c_p, c_f = st.columns(2)
    with c_p:
        parametro_selecionado = st.selectbox("Selecione o Indicador:", list(config_parametros.keys()))
    with c_f:
        frequencia = st.radio("Agrupamento:", ["Mensal", "Trimestral", "Anual"], horizontal=True, index=0)

    cfg = config_parametros[parametro_selecionado]
    coluna_alvo = cfg['col']

    if coluna_alvo in df_filtrado.columns:
        mapa_freq = {"Mensal": "ME", "Trimestral": "QE", "Anual": "YE"}
        
        df_proc = df_filtrado.copy()
        df_proc['data'] = pd.to_datetime(df_proc['data'])
        df_proc[coluna_alvo] = pd.to_numeric(df_proc[coluna_alvo], errors='coerce')

        df_temp = df_proc.set_index('data').resample(mapa_freq[frequencia])[coluna_alvo].mean().reset_index()
        
        if df_temp[coluna_alvo].notna().sum() > 0:
            
            fig2, ax = plt.subplots(figsize=(10, 4)) 
            mark = 's' if frequencia == 'Anual' else 'o'
            
            sns.lineplot(
                data=df_temp, x='data', y=coluna_alvo,
                marker=mark, markersize=7,
                color=cfg['cor'], linewidth=2, label=f'Média {frequencia}'
            )

            lim = cfg['limite']
            if cfg['tipo_lim'] == 'min':
                plt.axhline(lim, color='red', linestyle='--', alpha=0.7)
                plt.fill_between(df_temp['data'], 0, lim, color='red', alpha=0.1)
            elif cfg['tipo_lim'] == 'max':
                plt.axhline(lim, color='red', linestyle='--', alpha=0.7)
                max_y = df_temp[coluna_alvo].max()
                teto = max(max_y, lim) * 1.2 if pd.notna(max_y) else lim * 1.2
                plt.fill_between(df_temp['data'], lim, teto, color='red', alpha=0.1)
            elif cfg['tipo_lim'] == 'range':
                plt.axhline(lim[0], color='red', linestyle='--')
                plt.axhline(lim[1], color='red', linestyle='--')
                plt.fill_between(df_temp['data'], 0, lim[0], color='red', alpha=0.1)
                plt.fill_between(df_temp['data'], lim[1], 14, color='red', alpha=0.1)
                plt.ylim(4, 10)

            if frequencia == "Anual":
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
                ax.xaxis.set_major_locator(mdates.YearLocator())
                plt.xticks(rotation=0)
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%b/%y'))
                plt.xticks(rotation=45)

            plt.title(f"{parametro_selecionado} - Visão {frequencia}", fontsize=12)
            plt.ylabel(cfg['ylabel'], fontsize=10)
            plt.xlabel("")
            plt.grid(True, linestyle=':', alpha=0.5)
            plt.legend(frameon=True, loc='best')
            plt.tight_layout()
            
            st.pyplot(fig2)
        else:
            st.info(f"Sem dados suficientes de {parametro_selecionado} para gerar o gráfico.")
    else:
        st.warning(f"A coluna '{coluna_alvo}' não existe no arquivo de dados.")

with tab3:
    st.markdown("### Análise Científica (Correlação e Qualidade)")
    
    if not df_filtrado.empty:
        cols_analise = [
            "ph", "od", "turbidez", "temperatura_agua", "condutividade", "solidos_dissolvidos","nitrogenio","salinidade","fosforo"
        ]
        cols_existentes = [c for c in cols_analise if c in df_filtrado.columns]
        
        df_cientifico = df_filtrado[cols_existentes].copy()
        df_cientifico = df_cientifico.replace(0.0, float('nan'))
        
        col_c1, col_c2 = st.columns([1,1])
        
        with col_c1:
            st.markdown("**Disponibilidade de Dados**")
            total = len(df_cientifico)
            if total > 0:
                preenchimento = (df_cientifico.count() / total) * 100
                df_missing = pd.DataFrame(preenchimento, columns=['% Preenchimento']).sort_values('% Preenchimento', ascending=True)
                
                fig_miss, ax_miss = plt.subplots(figsize=(6,6))
                sns.barplot(x=df_missing['% Preenchimento'], y= df_missing.index, ax= ax_miss, palette="viridis", hue=df_missing.index)
                ax_miss.set_xlim(0,105)
                ax_miss.grid(axis="x", linestyle="--", alpha=0.5)
                st.pyplot(fig_miss)
            else:
                st.warning("Sem dados para calcular disponibilidade.")
            
        with col_c2:
            st.markdown("**Correlação de Pearson**")
            corr = df_cientifico.corr()
            fig_corr, ax_corr = plt.subplots(figsize=(8,8))
            mask = np.triu(np.ones_like(corr, dtype=bool))
            sns.heatmap(corr, mask=mask, cmap="coolwarm", vmin=-1, vmax=1, center=0, annot=True, fmt=".2f", square=True, cbar_kws={"shrink": .5})
            st.pyplot(fig_corr)
            
        st.divider()
        st.markdown("**💡 Insight Automático:**")
        if 'ph' in corr.columns and 'turbidez' in corr.columns:
            val = corr.loc['ph', 'turbidez']
            st.write(f"Correlação pH vs Turbidez: {val:.2f}")
    
    else:
        st.warning("Sem dados suficientes para análise estatística")