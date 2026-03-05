import streamlit as st
import datetime
import plotly.express as px
from client import WeniChatsEngineClient
from utils import calculate_sac_metrics

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Oscar Calçados | SAC Analytics", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

def main():
    st.title("📊 Dashboard SAC - Oscar Calçados")
    st.caption("Análise de métricas de atendimento humano - API Weni v2")

    # --- SIDEBAR FILTROS ---
    with st.sidebar:
        st.image("https://media.licdn.com/dms/image/v2/C4D0BAQHZLjg07E3QIQ/company-logo_200_200/company-logo_200_200/0/1630575950724/grupo_oscar_cal_ados_logo?e=2147483647&v=beta&t=8RZBpOizPkdB8fBgMzMI-MPcw0DM7wZDxx8YBrukfFY", width=150)
        st.header("⚙️ Configurações")
        api_token = st.text_input("API Token", type="password")
        
        range_date = st.date_input(
            "Período de Análise",
            value=(datetime.date.today() - datetime.timedelta(days=7), datetime.date.today())
        )

        st.divider()
        st.header("🎯 Filtros de Segmentação")
        
        # Placeholder para o seletor de setor (será preenchido após carregar os dados)
        container_setor = st.container()

    if not api_token or len(range_date) < 2:
        st.info("Insira o token de acesso e o período para carregar os dados.")
        return

    # --- CARREGAMENTO DE DADOS ---
    client = WeniChatsEngineClient(api_token)
    df_raw = client.fetch_metrics(range_date[0], range_date[1])

    if df_raw.empty:
        st.warning("Nenhum dado encontrado para o filtro selecionado.")
        return

    # --- LÓGICA DE FILTRO POR SETOR ---
    # Extraímos os setores únicos do dataframe processado pelo client
    setores_disponiveis = sorted(df_raw['sector_name'].unique().tolist())
    if '' in setores_disponiveis: setores_disponiveis.remove('') # Remove vazios da lista
    
    with container_setor:
        setores_selecionados = st.multiselect(
            "Filtrar por Setor",
            options=setores_disponiveis,
            default=setores_disponiveis,
            help="Selecione um ou mais setores. Deixe vazio para ver todos."
        )

    # Aplicando o filtro no DataFrame
    if setores_selecionados:
        df_filtered = df_raw[df_raw['sector_name'].isin(setores_selecionados)]
    else:
        df_filtered = df_raw

    # Recalcula métricas com base no DF filtrado
    metrics = calculate_sac_metrics(df_filtered)

    # --- DASHBOARD LAYOUT ---
    if df_filtered.empty:
        st.error("Não há dados para os setores selecionados.")
        return

    # KPIs Principais
    st.subheader("🚀 Indicadores de Performance")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    # Métrica alterada conforme solicitado
    kpi1.metric("Total de Atendimentos", metrics["total_calls"])
    
    # Clientes que só chamaram uma vez (FCR em valor absoluto)
    kpi2.metric("Atendimentos Únicos", metrics["single_contact"], help="Clientes que entraram em contato apenas uma vez.")
    
    # Clientes que geraram mais de um chamado
    kpi3.metric("Clientes Reincidentes", metrics["recurrent_clients"], delta_color="inverse", help="Quantidade de URNs distintos que possuem 2 ou mais chamados no período.")
    
    # Métrica de FCR (Porcentagem de chamados não reincidentes sobre o total)
    kpi4.metric(
        label="Taxa de FCR", 
        value=f"{metrics['fcr_rate']}%",
        help="Razão entre chamados de contatos únicos e o total de atendimentos abertos no período."
    )

    st.divider()

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("🚩 Assuntos Frequentes (Tags)")
        top_tags = metrics["top_tags"]
        if not top_tags.empty:
            # Filtro de tags vazias para o gráfico
            top_tags = top_tags[top_tags['tag_list'] != ""]
            fig = px.bar(top_tags.head(10), x='Frequência', y='tag_list', 
                         orientation='h', color='Frequência',
                         color_continuous_scale='Reds', template='plotly_white')
            fig.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("🔄 Reincidência por Assunto")
        st.dataframe(
            metrics["reincidence_table"],
            column_config={
                "urn": "Cliente",
                "tag_list": "Assunto",
                "sector_name": "Setor",
                "qtd_salas": st.column_config.NumberColumn("Qtd. Salas", format="%d 🏢")
            },
            hide_index=True,
            use_container_width=True
        )

    st.divider()
    # --- NOVA SEÇÃO: REINCIDÊNCIA POR PEDIDO ---
    st.subheader("📦 Chamados por Pedido (Reincidência)")
    st.markdown("Identificação de múltiplos tickets abertos para o mesmo número de pedido (16 primeiros caracteres do protocolo).")

    if not metrics["order_reincidence"].empty:
        st.dataframe(
            metrics["order_reincidence"],
            column_config={
                "ID do Pedido": st.column_config.TextColumn("Número do Pedido"),
                "Tickets Relacionados": st.column_config.ListColumn("Protocolos Identificados"),
                "Setores": st.column_config.ListColumn("Setores Envolvidos"),
                "Qtd Tickets": st.column_config.NumberColumn("Qtd. Atendimentos", format="%d 🎫")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Nenhum pedido com múltiplos tickets foi detectado no período selecionado.")

    with st.expander("🔍 Ver Base de Dados Completa"):
        available_cols = ['created_on', 'urn', 'sector_name', 'protocol', 'tag_list', 'interaction_time']
        display_cols = [c for c in available_cols if c in df_filtered.columns]
        st.dataframe(df_filtered[display_cols], use_container_width=True)

if __name__ == "__main__":
    main()