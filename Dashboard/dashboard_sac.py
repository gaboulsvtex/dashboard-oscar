import streamlit as st
import datetime
import pandas as pd
import plotly.express as px
import concurrent.futures
import threading
import time
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx
from client import WeniChatsEngineClient, WeniSupervisorClient, WeniFlowsClient, WeniEventsClient
from utils import calculate_sac_metrics, calculate_csat_metrics

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
        "conv_key": st.secrets["OSCAR_CALCADOS"]["CONVERSATIONS_KEY"],
        "flows_token": st.secrets["OSCAR_CALCADOS"]["FLOWS_TOKEN"],
        "flow_uuid": "ed542aa7-003d-4f64-b95d-8b236a1c094b"
    },
    "Paquetá Esportes": {
        "sac_sector": "Paquetá Esportes",
        "project_uuid": "95c89c57-7591-46bc-9845-add5f98e5488",
        "conv_key": st.secrets["PAQUETA_ESPORTES"]["CONVERSATIONS_KEY"],
        "flows_token": st.secrets["PAQUETA_ESPORTES"]["FLOWS_TOKEN"],
        "flow_uuid": "26f21437-8f7c-4767-a6a6-fb22ac6ac065"
    },
    "Paquetá Calçados": {
        "sac_sector": "paquetá",
        "project_uuid": "953c5de8-3055-411a-ab7d-5f41906bfe2b",
        "conv_key": st.secrets["PAQUETA_CALCADOS"]["CONVERSATIONS_KEY"],
        "flows_token": st.secrets["PAQUETA_CALCADOS"]["FLOWS_TOKEN"],
        "flow_uuid": "f7b5e140-4e65-44d2-9e7d-cb4497e1c478"
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

    if not projetos_selecionados:
        st.warning("Selecione pelo menos um projeto no menu lateral.")
        return

    if page == "Atendimento Humano (SAC)":
        render_sac_page(
            range_date,
            projetos_selecionados
        )
    else:
        render_ai_page(
            range_date,
            projetos_selecionados
        )

def render_sac_page(dates, selected_projects): 
    st.title("📊 Dashboard SAC - Atendimento Humano")

    # --- CHATS ENGINE ---
    client_chats_engine = WeniChatsEngineClient(st.secrets["TOKENS"]["CHATS_ENGINE_TOKEN"])
    df_raw = client_chats_engine.fetch_metrics(dates[0], dates[1])

    if df_raw.empty:
        st.warning("Nenhum dado encontrado para o período selecionado.")
        return

    # Filtro dinâmico: une os nomes de setores dos projetos selecionados
    setores = [PROJECT_CONFIGS[p]["sac_sector"] for p in selected_projects]
    # Filtra o DataFrame se o setor contiver qualquer uma das strings na lista
    df_filtered = df_raw[df_raw['sector.name'].str.contains('|'.join(setores), case=False, na=False)]

    metrics = calculate_sac_metrics(df_filtered)

    # --- FLOWS ---
    consolidated_csat = []

    for p_name in selected_projects:
        config = PROJECT_CONFIGS[p_name]
        flow_client = WeniFlowsClient(config["flows_token"], config["flow_uuid"])
        consolidated_csat.extend(flow_client.fetch_csat_data(dates[0], dates[1]))

    csat_metrics = calculate_csat_metrics(consolidated_csat)
    setores = [PROJECT_CONFIGS[p]["sac_sector"] for p in selected_projects]
    df_filtered = df_raw[df_raw['sector.name'].str.contains('|'.join(setores), case=False, na=False)]
    sac_metrics = calculate_sac_metrics(df_filtered)

    # KPIs Principais
    st.subheader("🚀 Indicadores de Performance")
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    
    # Métrica alterada conforme solicitado
    kpi1.metric("Total de Atendimentos ENCERRADOS", sac_metrics["total_calls"])
    
    # Clientes que só chamaram uma vez (FCR em valor absoluto)
    kpi2.metric("Atendimentos Únicos", sac_metrics["single_contact"], help="Clientes que entraram em contato apenas uma vez.")
    
    # Clientes que geraram mais de um chamado
    kpi3.metric("Clientes Reincidentes", sac_metrics["recurrent_clients"], delta_color="inverse", help="Quantidade de URNs distintos que possuem 2 ou mais chamados no período.")
    
    # Métrica de FCR (Porcentagem de chamados não reincidentes sobre o total)
    kpi4.metric(
        label="Taxa de FCR", 
        value=f"{sac_metrics['fcr_rate']}%",
        help="Razão entre chamados de contatos únicos e o total de atendimentos abertos no período."
    )

    kpi5.metric(
        "CSAT Positivo ⭐", 
        f"{csat_metrics['positive_percentage']}%", 
        help=f"Baseado em {csat_metrics['count']} avaliações (porcentagem de notas 4 e 5)"
    )

    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("⏱️ Tempos Médios de Atendimento")
    
    t1, t2, t3, t4 = st.columns(4)
    t1.metric(
        "Tempo Médio em Espera", 
        sac_metrics["avg_waiting_time"], 
        help="Média do tempo que o contato aguardou até ser atribuído a um atendente humano."
    )
    t2.metric(
        "Tempo p/ 1ª Resposta", 
        sac_metrics["avg_first_response_time"], 
        help="Média do tempo até a primeira interação do agente humano."
    )
    t3.metric(
        "Tempo Médio de Resposta", 
        sac_metrics["avg_message_response_time"], 
        help="Média de tempo geral entre uma mensagem do cliente e a resposta do agente."
    )
    t4.metric(
        "Duração da Conversa", 
        sac_metrics["avg_interaction_time"], 
        help="Tempo total médio de duração da sala desde a abertura até o encerramento."
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

        st.write("---")

        st.subheader("⭐ Distribuição CSAT")
        if csat_metrics["count"] > 0:
            # Criação do gráfico de barras horizontais
            fig_csat = px.bar(
                csat_metrics["dist"], 
                x='Proporção', 
                y='Categoria', 
                orientation='h',
                text='Texto', # O texto criado no utils.py (Ex: 80.0% (4))
                color='Nota',
                color_continuous_scale="RdYlGn", # Escala de cor: Vermelho (1) ao Verde (5)
                range_color=[1, 5] # Fixa os extremos das cores
            )
            
            # Ajustes visuais de layout do gráfico
            fig_csat.update_layout(
                xaxis_title="Proporção das Avaliações (%)",
                yaxis_title="",
                showlegend=False,
                height=350,
                xaxis=dict(range=[0, 115]) # Dá margem extra na direita para caber o texto longo
            )
            
            # Posiciona o texto ao lado direito (fora) de cada barra
            fig_csat.update_traces(
                textposition='outside',
                textfont_size=14,
                cliponaxis=False # Evita que textos muito longos sejam cortados na borda
            )
            
            st.plotly_chart(fig_csat, use_container_width=True)
        else:
            st.info("Nenhuma avaliação CSAT encontrada no período filtrado.")

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

def fetch_project_data(p_name, config, dates):
    # Função auxiliar para buscar dados de um projeto (roda em paralelo)
    print(f"[{time.strftime('%H:%M:%S')}] 🟢 INICIANDO: {p_name}")
    token_projeto = config["conv_key"]
    uuid_projeto = config["project_uuid"]
    flows_token = config["flows_token"]
    
    # 1. Busca conversas
    client_supervisor = WeniSupervisorClient(uuid_projeto, token_projeto)
    data = client_supervisor.fetch_ai_conversations(dates[0], dates[1])
    
    # 2. Busca eventos de CSAT da IA
    client_events = WeniEventsClient(flows_token)
    csat_evals = client_events.fetch_csat_events(dates[0], dates[1])
    
    print(f"[{time.strftime('%H:%M:%S')}] 🔴 FINALIZANDO: {p_name}")
    return p_name, data, csat_evals

def render_ai_page(dates, selected_projects):
    st.title("📊 Métricas de IA - Consolidado")
    
    total_conversas = 0
    ai_assisted_total = 0
    not_assisted_total = 0
    transferred_total = 0
    dfs_projetos = [] # Lista limpa para acumular DataFrames
    ai_csat_evaluations = []
    futures = {}

    # pegando o contexto atual da sessão do streamlit
    ctx = get_script_run_ctx()

    def fetch_with_context(p_name, config, dates):
        add_script_run_ctx(threading.current_thread(), ctx)
        return fetch_project_data(p_name, config, dates)

    # Loop para buscar dados de cada projeto
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected_projects)) as executor:
        for p_name in selected_projects:
            config = PROJECT_CONFIGS[p_name]
            future = executor.submit(fetch_with_context, p_name, config, dates)
            futures[future] = p_name
            
        for future in concurrent.futures.as_completed(futures):
            p_name = futures[future]
            try:
                _, data, csat_evals = future.result()
                
                ai_csat_evaluations.extend(csat_evals)
                
                if data:
                    summary = data.get("status_summary", {})
                    total_conversas += data.get("count", 0)
                    ai_assisted_total += summary.get("0", 0)
                    not_assisted_total += summary.get("1", 0)
                    transferred_total += summary.get("4", 0)
                    
                    if data.get("results"):
                        df_temp = pd.DataFrame(data["results"])
                        df_temp["projeto_origem"] = p_name
                        dfs_projetos.append(df_temp)
                        
            except Exception as exc:
                st.error(f"O projeto {p_name} gerou um erro na busca: {exc}")

    ai_csat_metrics = calculate_csat_metrics(ai_csat_evaluations)

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
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Total de Contatos Únicos", 
        contatos_unicos, 
        help="Quantidade de clientes diferentes (URNs únicos) que interagiram."
    )
    m2.metric(
        "Contatos Recorrentes", 
        contatos_recorrentes, 
        help="Clientes que conversaram com a IA mais de uma vez no período selecionado."
    )
    m3.metric(
        "CSAT Positivo ⭐", 
        f"{ai_csat_metrics['positive_percentage']}%", 
        help=f"Baseado em {ai_csat_metrics['count']} avaliações (porcentagem de notas 4 e 5)."
    )

    st.divider()
    
    col_ai_left, col_ai_right = st.columns([1, 1])

    with col_ai_left:
        # --- GRÁFICO: ASSUNTOS MAIS COMUNS (TOPICS) ---
        st.subheader("🚩 Assuntos mais comuns")
        
        # Filtrar valores nulos ou vazios na coluna topic
        if 'topic' in df_ai.columns:
            df_topics = df_ai.dropna(subset=['topic']).copy()
            df_topics = df_topics[df_topics['topic'].astype(str).str.strip() != ""]
            
            if not df_topics.empty:
                # Contagem de frequência dos assuntos
                top_topics = df_topics['topic'].value_counts().reset_index()
                top_topics.columns = ['Assunto', 'Frequência']
                
                # Gráfico de barras horizontais do Plotly
                fig_topics = px.bar(
                    top_topics.head(10), # Pega os 10 assuntos mais frequentes
                    x='Frequência', 
                    y='Assunto', 
                    orientation='h', 
                    color='Frequência',
                    color_continuous_scale='Blues', # Utilizando azul para diferenciar do vermelho do SAC
                    template='plotly_white'
                )
                fig_topics.update_layout(
                    yaxis={'categoryorder':'total ascending'}, 
                    showlegend=False,
                    height=350
                )
                st.plotly_chart(fig_topics, use_container_width=True)
            else:
                st.info("Nenhum assunto (topic) foi classificado nas conversas filtradas.")
    
    with col_ai_right:
        st.subheader("⭐ Distribuição CSAT (IA)")
        if ai_csat_metrics["count"] > 0:
            fig_csat_ai = px.bar(
                ai_csat_metrics["dist"], 
                x='Proporção', 
                y='Categoria', 
                orientation='h',
                text='Texto',
                color='Nota',
                color_continuous_scale="RdYlGn",
                range_color=[1, 5]
            )
            
            fig_csat_ai.update_layout(
                xaxis_title="Proporção das Avaliações (%)",
                yaxis_title="",
                showlegend=False,
                height=350,
                xaxis=dict(range=[0, 115])
            )
            
            fig_csat_ai.update_traces(
                textposition='outside',
                textfont_size=14,
                cliponaxis=False
            )
            st.plotly_chart(fig_csat_ai, use_container_width=True)
        else:
            st.info("Nenhuma avaliação CSAT (IA) encontrada no período.")

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