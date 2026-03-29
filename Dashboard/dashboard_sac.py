import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
from client import WeniChatsEngineClient, WeniSupervisorClient
from utils import calculate_sac_metrics

# --- CONFIGURAÇÃO VISUAL ---
st.set_page_config(page_title="Oscar Calçados | Analytics", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# Mapeamento de Configurações por Projeto
PROJECT_CONFIGS = {
    "Oscar Calçados": {
        "sac_sector": "Oscar Calçados",
        "project_uuid": "9a69cb5f-af0e-4a59-b53c-66c814d56fe7",
        "token_idx": 1
    },
    "Paquetá Esportes": {
        "sac_sector": "Paquetá Esportes",
        "project_uuid": "95c89c57-7591-46bc-9845-add5f98e5488",
        "token_idx": 2
    },
    "Paquetá Calçados": {
        "sac_sector": "paquetá",
        "project_uuid": "953c5de8-3055-411a-ab7d-5f41906bfe2b",
        "token_idx": 3
    }
}

def main():

    # --- SIDEBAR COMUM ---
    with st.sidebar:
        st.image("https://media.licdn.com/dms/image/v2/C4D0BAQHZLjg07E3QIQ/company-logo_200_200/company-logo_200_200/0/1630575950724/grupo_oscar_cal_ados_logo?e=2147483647&v=beta&t=8RZBpOizPkdB8fBgMzMI-MPcw0DM7wZDxx8YBrukfFY", width=150)
        
        st.header("📂 Navegação")
        page = st.radio(
            "Selecione a Visualização",
            ["Atendimento Humano (SAC)", "Conversas com IA"]
        )
        
        st.divider()
        st.header("⚙️ Configurações")
        raw_tokens = st.text_input(
            "Tokens (t1 / t2 / t3 / t4)",
            type="password",
            help="Insira os 4 tokens separados por barra"
        )
        
        range_date = st.date_input(
            "Período de Análise",
            value=(datetime.date.today() - datetime.timedelta(days=7), datetime.date.today())
        )

        st.header("🎯 Filtros de Segmentação")
        projetos_selecionados = st.multiselect(
            "Filtrar por Projeto",
            options=list(PROJECT_CONFIGS.keys()),
            help="Selecione um ou mais projetos para ver os dados.",
            default=list(PROJECT_CONFIGS.keys())
        )
    
    # Validação de Tokens
    tokens = [t.strip() for t in raw_tokens.split("/")] if raw_tokens else []
    if len(tokens) < 4:
        st.info("Por favor, insira os 4 tokens no formato: token1 / token2 / token3 / token4")
        return

    if not projetos_selecionados:
        st.warning("Selecione pelo menos um projeto no menu lateral.")
        return

    if page == "Atendimento Humano (SAC)":
        render_sac_page(
            tokens[0],
            range_date,
            projetos_selecionados
        )
    else:
        render_ai_page(
            tokens,
            range_date,
            projetos_selecionados
        )

def render_sac_page(token, dates, selected_projects): 
    st.title("📊 Dashboard SAC - Atendimento Humano")
    client = WeniChatsEngineClient(token)
    df_raw = client.fetch_metrics(dates[0], dates[1])

    if df_raw.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return

    # Filtro dinâmico: une os nomes de setores dos projetos selecionados
    setores = [PROJECT_CONFIGS[p]["sac_sector"] for p in selected_projects]
    # Filtra o DataFrame se o setor contiver qualquer uma das strings na lista
    df_filtered = df_raw[df_raw['sector.name'].str.contains('|'.join(setores), case=False, na=False)]

    metrics = calculate_sac_metrics(df_filtered)

    # KPIs Principais
    st.subheader("🚀 Indicadores de Performance")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    # Métrica alterada conforme solicitado
    kpi1.metric("Total de Atendimentos ENCERRADOS", metrics["total_calls"])
    
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

def render_ai_page(all_tokens, dates, selected_projects):
    st.title("🤖 Métricas de IA - Consolidado")
    
    total_conversas = 0
    ai_assisted_total = 0
    not_assisted_total = 0
    transferred_total = 0
    dfs_projetos = [] # Lista limpa para acumular DataFrames

    # Loop para buscar dados de cada projeto
    for p_name in selected_projects:
        config = PROJECT_CONFIGS[p_name]
        token_projeto = all_tokens[config["token_idx"]]
        uuid_projeto = config["project_uuid"]
        
        client = WeniSupervisorClient(uuid_projeto, token_projeto)
        data = client.fetch_ai_conversations(dates[0], dates[1])
        
        if data:
            summary = data.get("status_summary", {})
            total_conversas += data.get("count", 0)
            ai_assisted_total += summary.get("0", 0)
            not_assisted_total += summary.get("1", 0)
            transferred_total += summary.get("4", 0)
            
            if data.get("results"):
                # Transforma direto em DF para evitar mutação do dicionário cacheado
                df_temp = pd.DataFrame(data["results"])
                df_temp["projeto_origem"] = p_name
                dfs_projetos.append(df_temp)

    # --- CÁLCULO DAS MÉTRICAS DE CONTATO ---
    if dfs_projetos:
        # Junta os DataFrames de todos os projetos de forma segura
        df_ai = pd.concat(dfs_projetos, ignore_index=True)
        
        # Filtra os contatos vazios ou nulos (Para a IA não contabilizar ausência de número como reincidência)
        df_valid_urns = df_ai.dropna(subset=['contact_urn'])
        df_valid_urns = df_valid_urns[df_valid_urns['contact_urn'].astype(str).str.strip() != ""]
        
        # Cálculos de contatos
        contatos_unicos = df_valid_urns['contact_urn'].nunique()
        urn_counts = df_valid_urns['contact_urn'].value_counts()
        contatos_recorrentes = len(urn_counts[urn_counts > 1])
    else:
        contatos_unicos = 0
        contatos_recorrentes = 0
        df_ai = pd.DataFrame()

    # --- EXIBIÇÃO DOS KPIS ---
    st.subheader(f"Performance Consolidada: {', '.join(selected_projects)}")
    
    # Cálculos de Porcentagem
    pct_atendidas_ia = (ai_assisted_total / total_conversas * 100) if total_conversas > 0 else 0.0
    pct_nao_atendidas = (not_assisted_total / total_conversas * 100) if total_conversas > 0 else 0.0
    pct_transferidas = (transferred_total / total_conversas * 100) if total_conversas > 0 else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de Conversas", total_conversas)
    c2.metric(
        "Atendidas pela IA", 
        f"{pct_atendidas_ia:.1f}%", 
        delta=f"{ai_assisted_total} conversas", 
        delta_color="off"
    )
    c3.metric(
        "Não Atendidas pela IA", 
        f"{pct_nao_atendidas:.1f}%", 
        delta=f"{not_assisted_total} conversas", 
        delta_color="off"
    )
    c4.metric(
        "Transferidas (Humano)", 
        f"{pct_transferidas:.1f}%", 
        delta=f"{transferred_total} conversas", 
        delta_color="off"
    )

    st.write("---")
    m1, m2 = st.columns(2)
    m1.metric("Total de Contatos Únicos", contatos_unicos, 
              help="Quantidade de clientes diferentes (URNs únicos) que interagiram.")
    m2.metric("Contatos Recorrentes", contatos_recorrentes, 
              help="Clientes que conversaram com a IA mais de uma vez no conjunto selecionado.")

    st.divider()
    
    if not df_ai.empty:
        st.subheader("💬 Detalhamento das Conversas")
        df_ai['created_at'] = pd.to_datetime(df_ai['created_at'])
        df_ai = df_ai.sort_values(by='created_at', ascending=False)
        
        cols = ['projeto_origem', 'created_at', 'status', 'contact_urn', 'topic']
        st.dataframe(df_ai[cols], use_container_width=True)
    else:
        st.info("Nenhuma conversa encontrada para os filtros aplicados.")

if __name__ == "__main__":
    main()