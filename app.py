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


# Filtros
df_raw['ano_filtro'] = df_raw['data'].dt.year.astype(int)
df_raw['mes_filtro'] = df_raw['data'].dt.month.astype(int)

st.sidebar.header("Filtros de Análise")

# Filtro do ano
anos_disponiveis = sorted(df_raw['ano_filtro'].unique(), reverse=True)
anos_selecionados = st.sidebar.multiselect("Selecione os anos:", anos_disponiveis, default=anos_disponiveis)

# Filtro do mês
MESES_NOMES = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}
meses_disponiveis = sorted(df_raw['mes_filtro'].unique())
meses_selecionados = st.sidebar.multiselect(
    "Selecione os meses:",
    options=meses_disponiveis,
    default=meses_disponiveis,
    format_func=lambda m: MESES_NOMES.get(m, str(m))
)

# Filtro de rio
rios_disponiveis = sorted(df_raw['rio'].unique())
rios_selecionados = st.sidebar.multiselect("Selecione os rios:", rios_disponiveis, default=rios_disponiveis)

# Filtro por parâmetro (foco de análise) — usado nas abas de Ranking e Boxplot
PARAMETROS_CONAMA = {
    "Todos os parâmetros": {"col": None, "limite": None, "tipo_lim": None},
    "pH": {"col": "ph", "limite": [6.0, 9.0], "tipo_lim": "range", "status": "status_ph"},
    "Oxigênio Dissolvido (OD)": {"col": "od", "limite": 5.0, "tipo_lim": "min", "status": "status_od"},
    "Turbidez": {"col": "turbidez", "limite": 100.0, "tipo_lim": "max", "status": "status_turbidez"},
}
parametro_foco = st.sidebar.selectbox(
    "Parâmetro em foco:",
    list(PARAMETROS_CONAMA.keys()),
    help="Define o parâmetro destacado nas análises de Ranking e Boxplot."
)

# Aplicação de filtros
df_filtrado = df_raw[
    (df_raw['ano_filtro'].isin(anos_selecionados)) &
    (df_raw['mes_filtro'].isin(meses_selecionados)) &
    (df_raw['rio'].isin(rios_selecionados))
]

# Indicadores principais (KPIs)
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
        'status_od': 'Oxigênio Dissolvido',
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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Conformidade por Parâmetro",
    "Evolução Temporal (OD)",
    "Estatística Científica",
    "Ranking de Pontos Críticos",
    "Distribuição por Rio (Boxplot)"
    ])

with tab1:
    st.markdown("### Conformidade comparada — CONAMA 357/2005")

    if df_filtrado.empty:
        st.warning("Sem dados para os filtros atuais.")
    else:
        # Rótulos considerados como violação / conformidade / sem dado
        ROTULOS_FORA = {'Fora do Padrão', 'Não Conforme', 'Fora', 'Ruim', 'Péssimo'}
        ROTULOS_OK   = {'Dentro do Padrão', 'Conforme', 'OK', 'Bom', 'Ótimo'}
        ROTULOS_SEM  = {'Sem Dado', 'Sem dado', ''}

        def classificar_rotulo(v):
            if pd.isna(v) or v in ROTULOS_SEM:
                return 'Sem Dado'
            if v in ROTULOS_FORA:
                return 'Fora do Padrão'
            if v in ROTULOS_OK:
                return 'Dentro do Padrão'
            return 'Sem Dado'

        parametros_conf = [
            ('status_ph', 'pH'),
            ('status_od', 'Oxigênio Dissolvido'),
            ('status_turbidez', 'Turbidez'),
        ]

        linhas = []
        for col_status, nome in parametros_conf:
            if col_status not in df_filtrado.columns:
                continue
            serie = df_filtrado[col_status].apply(classificar_rotulo)
            cont = serie.value_counts()
            total_valido = int(cont.get('Dentro do Padrão', 0) + cont.get('Fora do Padrão', 0))
            total_amostras = int(serie.size)
            pct_fora = (cont.get('Fora do Padrão', 0) / total_valido * 100) if total_valido else 0.0
            linhas.append({
                'Parâmetro': nome,
                'Dentro do Padrão': int(cont.get('Dentro do Padrão', 0)),
                'Fora do Padrão':   int(cont.get('Fora do Padrão', 0)),
                'Sem Dado':         int(cont.get('Sem Dado', 0)),
                'Total Válido':     total_valido,
                'Total Amostras':   total_amostras,
                '% Fora':           pct_fora,
            })

        if not linhas:
            st.info("Nenhum status de conformidade disponível no dataset filtrado.")
        else:
            df_conf = pd.DataFrame(linhas)
            # Storytelling: ordena do pior para o melhor (maior % de violação no topo)
            df_conf = df_conf.sort_values('% Fora', ascending=True).reset_index(drop=True)

            # Identifica vilão para subtítulo dinâmico
            vilao = df_conf.sort_values('% Fora', ascending=False).iloc[0]
            if vilao['% Fora'] > 0:
                st.markdown(
                    f"<div style='font-size:1.05rem; color:#e74c3c;'>"
                    f"<b>{vilao['Parâmetro']}</b> é o parâmetro mais crítico: "
                    f"<b>{vilao['% Fora']:.1f}%</b> das amostras válidas estão fora do padrão CONAMA."
                    f"</div>",
                    unsafe_allow_html=True
                )
            else:
                st.success("Todas as amostras válidas estão dentro do padrão CONAMA 🎉")

            # Monta gráfico de barras empilhadas horizontais (% normalizado)
            df_plot_rows = []
            for _, r in df_conf.iterrows():
                tv = r['Total Válido'] if r['Total Válido'] else 1
                df_plot_rows.append({'Parâmetro': r['Parâmetro'], 'Status': 'Dentro do Padrão',
                                     'Qtd': r['Dentro do Padrão'],
                                     'Pct': r['Dentro do Padrão'] / tv * 100})
                df_plot_rows.append({'Parâmetro': r['Parâmetro'], 'Status': 'Fora do Padrão',
                                     'Qtd': r['Fora do Padrão'],
                                     'Pct': r['Fora do Padrão'] / tv * 100})
            df_plot = pd.DataFrame(df_plot_rows)

            fig_conf = px.bar(
                df_plot,
                x='Pct', y='Parâmetro',
                color='Status',
                orientation='h',
                color_discrete_map={'Dentro do Padrão': '#2ecc71', 'Fora do Padrão': '#e74c3c'},
                custom_data=['Qtd', 'Status'],
                category_orders={'Parâmetro': df_conf['Parâmetro'].tolist()}
            )
            # Anotação % no segmento vermelho (foco narrativo)
            for _, r in df_conf.iterrows():
                tv = r['Total Válido'] if r['Total Válido'] else 1
                pct_fora = r['Fora do Padrão'] / tv * 100
                if pct_fora > 0:
                    fig_conf.add_annotation(
                        x=100 - pct_fora / 2, y=r['Parâmetro'],
                        text=f"<b>{pct_fora:.0f}% fora</b>",
                        showarrow=False, font=dict(color='white', size=13)
                    )
            fig_conf.update_traces(
                hovertemplate="<b>%{y}</b><br>%{customdata[1]}: %{customdata[0]} amostras (%{x:.1f}%)<extra></extra>"
            )
            fig_conf.update_layout(
                barmode='stack',
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(title='% das amostras válidas', range=[0, 100], ticksuffix='%'),
                yaxis_title=None,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                plot_bgcolor='rgba(0,0,0,0)'
            )
            st.plotly_chart(fig_conf, width="stretch")

            # Tabela de apoio
            with st.expander("Ver números absolutos"):
                tabela = df_conf[['Parâmetro', 'Dentro do Padrão', 'Fora do Padrão',
                                   'Sem Dado', 'Total Amostras', '% Fora']].copy()
                tabela['% Fora'] = tabela['% Fora'].round(1)
                st.dataframe(
                    tabela,
                    column_config={
                        '% Fora': st.column_config.ProgressColumn(
                            '% Fora', format='%.1f%%', min_value=0, max_value=100
                        )
                    },
                    hide_index=True,
                    width="stretch"
                )


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
        janela_mm = {"Mensal": 6, "Trimestral": 4, "Anual": 3}[frequencia]

        df_proc = df_filtrado[['data', coluna_alvo]].copy()
        df_proc['data'] = pd.to_datetime(df_proc['data'])
        df_proc[coluna_alvo] = pd.to_numeric(df_proc[coluna_alvo], errors='coerce')
        # 0 = placeholder de "sem dado" no ETL — remove para não puxar a média
        df_proc = df_proc[df_proc[coluna_alvo] > 0].dropna()

        df_temp = (
            df_proc.set_index('data')
                   .resample(mapa_freq[frequencia])[coluna_alvo]
                   .mean()
                   .reset_index()
                   .dropna()
        )

        if not df_temp.empty:
            df_temp['mm'] = df_temp[coluna_alvo].rolling(window=janela_mm, min_periods=1).mean()

            # Classifica cada ponto como conforme x não-conforme p/ destacar violações
            lim = cfg['limite']
            def viola(v):
                if cfg['tipo_lim'] == 'min':
                    return v < lim
                if cfg['tipo_lim'] == 'max':
                    return v > lim
                if cfg['tipo_lim'] == 'range':
                    return (v < lim[0]) or (v > lim[1])
                return False

            df_temp['violou'] = df_temp[coluna_alvo].apply(viola) if cfg['tipo_lim'] != 'none' else False

            import plotly.graph_objects as go
            fig_t = go.Figure()

            # Camada 1: faixa crítica CONAMA (vermelho translúcido)
            x_full = df_temp['data']
            y_min = float(df_temp[coluna_alvo].min())
            y_max = float(df_temp[coluna_alvo].max())
            y_pad = (y_max - y_min) * 0.1 if y_max > y_min else 1.0

            if cfg['tipo_lim'] == 'min':
                fig_t.add_hrect(y0=y_min - y_pad, y1=lim, fillcolor='red',
                                opacity=0.08, line_width=0, layer='below',
                                annotation_text=f"Zona crítica (< {lim})",
                                annotation_position="bottom left",
                                annotation_font_color="#c0392b")
                fig_t.add_hline(y=lim, line_dash='dash', line_color='red', opacity=0.6)
            elif cfg['tipo_lim'] == 'max':
                fig_t.add_hrect(y0=lim, y1=y_max + y_pad, fillcolor='red',
                                opacity=0.08, line_width=0, layer='below',
                                annotation_text=f"Zona crítica (> {lim})",
                                annotation_position="top left",
                                annotation_font_color="#c0392b")
                fig_t.add_hline(y=lim, line_dash='dash', line_color='red', opacity=0.6)
            elif cfg['tipo_lim'] == 'range':
                fig_t.add_hrect(y0=y_min - y_pad, y1=lim[0], fillcolor='red',
                                opacity=0.08, line_width=0, layer='below')
                fig_t.add_hrect(y0=lim[1], y1=y_max + y_pad, fillcolor='red',
                                opacity=0.08, line_width=0, layer='below')
                fig_t.add_hline(y=lim[0], line_dash='dash', line_color='red', opacity=0.6)
                fig_t.add_hline(y=lim[1], line_dash='dash', line_color='red', opacity=0.6)

            # Camada 2: pontos brutos translúcidos (mostra o ruído)
            fig_t.add_trace(go.Scatter(
                x=df_temp['data'], y=df_temp[coluna_alvo],
                mode='lines+markers',
                name=f'Média {frequencia.lower()}',
                line=dict(color=cfg['cor'], width=1),
                marker=dict(size=6, color=cfg['cor'], opacity=0.45),
                opacity=0.55,
                hovertemplate="%{x|%b/%Y}<br>"+cfg['ylabel']+": %{y:.2f}<extra></extra>"
            ))

            # Camada 3: média móvel (a tendência narrativa)
            fig_t.add_trace(go.Scatter(
                x=df_temp['data'], y=df_temp['mm'],
                mode='lines',
                name=f'Tendência (MM {janela_mm}p)',
                line=dict(color=cfg['cor'], width=3.5),
                hovertemplate="%{x|%b/%Y}<br>Tendência: %{y:.2f}<extra></extra>"
            ))

            # Camada 4: pontos vermelhos destacando violações CONAMA
            df_viol = df_temp[df_temp['violou']]
            if not df_viol.empty:
                fig_t.add_trace(go.Scatter(
                    x=df_viol['data'], y=df_viol[coluna_alvo],
                    mode='markers',
                    name='Não conforme',
                    marker=dict(size=11, color='#e74c3c',
                                line=dict(color='white', width=1.5),
                                symbol='circle'),
                    hovertemplate="<b>Não conforme</b><br>%{x|%b/%Y}<br>"+cfg['ylabel']+": %{y:.2f}<extra></extra>"
                ))

            # Anotação automática no ponto mais crítico
            if cfg['tipo_lim'] in ('min', 'max', 'range') and not df_viol.empty:
                if cfg['tipo_lim'] == 'min':
                    pior = df_viol.loc[df_viol[coluna_alvo].idxmin()]
                    texto_pior = f"Mínima histórica: {pior[coluna_alvo]:.2f}"
                elif cfg['tipo_lim'] == 'max':
                    pior = df_viol.loc[df_viol[coluna_alvo].idxmax()]
                    texto_pior = f"Máxima histórica: {pior[coluna_alvo]:.2f}"
                else:
                    pior = df_viol.iloc[(df_viol[coluna_alvo] - (lim[0]+lim[1])/2).abs().argmax()]
                    texto_pior = f"Pico fora da faixa: {pior[coluna_alvo]:.2f}"
                fig_t.add_annotation(
                    x=pior['data'], y=pior[coluna_alvo],
                    text=f"<b>{pior['data'].strftime('%b/%Y')}</b><br>{texto_pior}",
                    showarrow=True, arrowhead=2, arrowcolor='#c0392b',
                    bgcolor='rgba(255,255,255,0.9)', bordercolor='#c0392b',
                    font=dict(color='#c0392b', size=11),
                    ax=40, ay=-50
                )

            fig_t.update_layout(
                title=f"{parametro_selecionado} — tendência {frequencia.lower()}",
                xaxis_title=None,
                yaxis_title=cfg['ylabel'],
                height=460,
                hovermode='x unified',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                margin=dict(l=10, r=10, t=60, b=10),
                plot_bgcolor='rgba(0,0,0,0)'
            )
            fig_t.update_xaxes(showgrid=True, gridcolor='rgba(128,128,128,0.15)')
            fig_t.update_yaxes(showgrid=True, gridcolor='rgba(128,128,128,0.15)')

            st.plotly_chart(fig_t, width="stretch")

            # Resumo narrativo embaixo do gráfico
            total_pts = len(df_temp)
            n_viol = int(df_temp['violou'].sum())
            if cfg['tipo_lim'] != 'none' and total_pts > 0:
                pct_viol = n_viol / total_pts * 100
                if n_viol == 0:
                    st.success(f"✅ Nos {total_pts} períodos analisados, **nenhum** violou o limite CONAMA.")
                else:
                    # Tendência: compara MM inicial e final
                    mm_ini = df_temp['mm'].iloc[0]
                    mm_fim = df_temp['mm'].iloc[-1]
                    if cfg['tipo_lim'] == 'min':
                        direcao = "melhorando 📈" if mm_fim > mm_ini else "piorando 📉"
                    elif cfg['tipo_lim'] == 'max':
                        direcao = "melhorando 📉" if mm_fim < mm_ini else "piorando 📈"
                    else:
                        direcao = "estável"
                    st.warning(
                        f"⚠️ **{n_viol} de {total_pts}** períodos ({pct_viol:.1f}%) violaram o limite CONAMA. "
                        f"Tendência geral (média móvel): **{direcao}** "
                        f"({mm_ini:.2f} → {mm_fim:.2f})."
                    )
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


with tab4:
    st.markdown("### Ranking de Pontos Críticos")
    st.caption("Pontos de coleta com maior frequência de não-conformidades segundo CONAMA 357/2005.")

    if df_filtrado.empty:
        st.warning("Sem dados para os filtros atuais.")
    else:
        cfg_foco = PARAMETROS_CONAMA[parametro_foco]
        df_rank = df_filtrado.copy()

        # Define a métrica de "falha" conforme o parâmetro em foco
        if cfg_foco["col"] is None:
            df_rank['_falha'] = (df_rank['indice_problemas'] > 0).astype(int)
            rotulo_metric = "Não-conformidades (qualquer parâmetro)"
        else:
            col_status = cfg_foco.get("status")
            if col_status and col_status in df_rank.columns:
                df_rank['_falha'] = df_rank[col_status].isin(
                    ['Fora do Padrão', 'Não Conforme', 'Fora']
                ).astype(int)
            else:
                df_rank['_falha'] = 0
            rotulo_metric = f"Não-conformidades de {parametro_foco}"

        # Agrupamento por rio + ponto (lat/lon arredondado p/ agrupar coletas próximas)
        df_rank['lat_r'] = df_rank['latitude'].round(4)
        df_rank['lon_r'] = df_rank['longitude'].round(4)

        ranking = df_rank.groupby(['rio', 'lat_r', 'lon_r']).agg(
            Amostras=('_falha', 'size'),
            Falhas=('_falha', 'sum')
        ).reset_index()
        ranking['Taxa_Falha_%'] = (ranking['Falhas'] / ranking['Amostras'] * 100).round(1)
        ranking = ranking.sort_values(['Falhas', 'Taxa_Falha_%'], ascending=False)

        top_n = st.slider("Mostrar top N pontos:", 5, 30, 10)
        ranking_top = ranking.head(top_n)

        col_r1, col_r2 = st.columns([1.2, 1])
        with col_r1:
            st.markdown(f"**{rotulo_metric}**")
            fig_rank = px.bar(
                ranking_top.sort_values('Falhas'),
                x='Falhas', y='rio', orientation='h',
                color='Taxa_Falha_%', color_continuous_scale='Reds',
                text='Falhas',
                hover_data={'lat_r': True, 'lon_r': True, 'Amostras': True, 'Taxa_Falha_%': True}
            )
            fig_rank.update_layout(height=400, margin=dict(l=0, r=0, t=10, b=0),
                                    xaxis_title="Nº de não-conformidades", yaxis_title=None)
            st.plotly_chart(fig_rank, width="stretch")

        with col_r2:
            st.markdown("**Detalhamento dos Pontos**")
            st.dataframe(
                ranking_top.rename(columns={
                    'rio': 'Rio', 'lat_r': 'Latitude', 'lon_r': 'Longitude'
                }),
                column_config={
                    "Taxa_Falha_%": st.column_config.ProgressColumn(
                        "Taxa Falha", format="%.1f%%", min_value=0, max_value=100
                    ),
                    "Amostras": st.column_config.NumberColumn("Amostras", format="%d"),
                    "Falhas": st.column_config.NumberColumn("Falhas", format="%d"),
                },
                hide_index=True,
                width="stretch"
            )


with tab5:
    st.markdown("### Distribuição dos Parâmetros por Rio")
    st.caption("Boxplot revela mediana, dispersão e outliers. Linhas tracejadas marcam o limite CONAMA 357/2005.")

    if df_filtrado.empty:
        st.warning("Sem dados para os filtros atuais.")
    else:
        cfg_foco = PARAMETROS_CONAMA[parametro_foco]

        # Se "Todos", deixa o usuário escolher um parâmetro para o boxplot
        if cfg_foco["col"] is None:
            opcoes_box = {k: v for k, v in PARAMETROS_CONAMA.items() if v["col"] is not None}
            escolha_box = st.selectbox("Escolha o parâmetro:", list(opcoes_box.keys()))
            cfg_box = opcoes_box[escolha_box]
            titulo_box = escolha_box
        else:
            cfg_box = cfg_foco
            titulo_box = parametro_foco

        col_alvo = cfg_box["col"]
        if col_alvo not in df_filtrado.columns:
            st.warning(f"Coluna '{col_alvo}' indisponível no dataset.")
        else:
            df_box = df_filtrado[['rio', col_alvo]].copy()
            df_box[col_alvo] = pd.to_numeric(df_box[col_alvo], errors='coerce')
            # 0 é placeholder para "sem dado" no ETL — remove para o boxplot
            df_box = df_box[df_box[col_alvo] > 0].dropna()

            if df_box.empty:
                st.info("Sem amostras válidas para o parâmetro selecionado.")
            else:
                ordem_rios = sorted(df_box['rio'].unique())
                fig_box = px.box(
                    df_box, x='rio', y=col_alvo,
                    points='outliers', color='rio',
                    category_orders={'rio': ordem_rios}
                )

                # Linhas de limite CONAMA
                if cfg_box["tipo_lim"] == "min":
                    fig_box.add_hline(y=cfg_box["limite"], line_dash="dash", line_color="red",
                                      annotation_text=f"Mín CONAMA ({cfg_box['limite']})")
                elif cfg_box["tipo_lim"] == "max":
                    fig_box.add_hline(y=cfg_box["limite"], line_dash="dash", line_color="red",
                                      annotation_text=f"Máx CONAMA ({cfg_box['limite']})")
                elif cfg_box["tipo_lim"] == "range":
                    fig_box.add_hline(y=cfg_box["limite"][0], line_dash="dash", line_color="red",
                                      annotation_text=f"Mín ({cfg_box['limite'][0]})")
                    fig_box.add_hline(y=cfg_box["limite"][1], line_dash="dash", line_color="red",
                                      annotation_text=f"Máx ({cfg_box['limite'][1]})")

                fig_box.update_layout(
                    height=500, showlegend=False,
                    xaxis_title=None, yaxis_title=titulo_box,
                    title=f"Distribuição de {titulo_box} por Rio"
                )
                fig_box.update_xaxes(tickangle=-30)
                st.plotly_chart(fig_box, width="stretch")

                # Resumo estatístico
                st.markdown("**Resumo estatístico por rio**")
                resumo = df_box.groupby('rio')[col_alvo].describe()[
                    ['count', 'mean', '50%', 'std', 'min', 'max']
                ].rename(columns={'50%': 'mediana', 'count': 'n'}).round(2)
                st.dataframe(resumo, width="stretch")