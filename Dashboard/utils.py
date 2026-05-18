import pandas as pd
import re

def extract_order_id(protocol):
    """
    Extrai o ID do pedido (16 primeiros caracteres) se o protocolo 
    seguir o padrão numérico '0000000000000-00-000000'.
    """
    if pd.isna(protocol) or not isinstance(protocol, str):
        return None
    
    # Verifica se o início do protocolo parece um ID de pedido (sequência numérica longa)
    # Padrão esperado: 13 dígitos + hífen + 2 dígitos
    if re.match(r'^\d{13}-\d{2}', protocol):
        return protocol[:16]
    return None

def format_seconds(seconds):
    """
    Formata um valor em segundos para um texto legível de horas, minutos e segundos.
    """
    if pd.isna(seconds) or seconds <= 0:
        return "0m 0s"
    
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    
    if h > 0:
        return f"{h}h {m}m {s}s"
    return f"{m}m {s}s"

def calculate_sac_metrics(df: pd.DataFrame):
    """Calcula estatísticas de chamados, reincidência, FCR e Pedidos."""
    if df.empty:
        return {
            "total_calls": 0,
            "single_contact": 0,
            "recurrent_clients": 0,
            "recurrent_clients_rate": 0.0,
            "fcr_calls": 0,
            "fcr_rate": 0.0,
            "top_tags": pd.DataFrame(),
            "reincidence_table": pd.DataFrame(),
            "order_reincidence": pd.DataFrame()
        }

    total_calls = len(df)
    urn_stats = df['urn'].value_counts()
    single_contacts = urn_stats[urn_stats == 1].count()
    tags_df = df.explode('tag_list')
    
    group_cols = ['urn', 'tag_list', 'sector_name'] if 'sector_name' in tags_df.columns else ['urn', 'tag_list']
    tag_reincidence = tags_df.groupby(group_cols).size().reset_index(name='qtd_salas')
    tag_reincidence = tag_reincidence[tag_reincidence['qtd_salas'] > 1].sort_values(by='qtd_salas', ascending=False)

    total_reincident_by_subject = int(tag_reincidence['qtd_salas'].sum())
    fcr_calls = max(0, total_calls - total_reincident_by_subject) 
    fcr_rate = (fcr_calls / total_calls * 100) if total_calls > 0 else 0.0
    
    recurrent_clients_count = urn_stats[urn_stats > 1].count()
    recurrent_clients_rate = (recurrent_clients_count / total_calls * 100) if total_calls > 0 else 0.0

    df['order_id'] = df['protocol'].apply(extract_order_id)
    df_orders = df[df['order_id'].notna()].copy()
    order_reincidence = df_orders.groupby('order_id').agg({
        'protocol': lambda x: list(set(x)),
        'sector_name': lambda x: list(set([s for s in x if s])),
        'uuid': 'count'
    }).reset_index()
    order_reincidence.columns = ['ID do Pedido', 'Protocolos Relacionados','Setor', 'Qtd Tickets']
    order_reincidence = order_reincidence[order_reincidence['Qtd Tickets'] > 1].sort_values(by='Qtd Tickets', ascending=False)

    return {
        "total_calls": total_calls,
        "single_contact": single_contacts,
        "recurrent_clients": recurrent_clients_count,
        "recurrent_clients_rate": round(recurrent_clients_rate, 2),
        "fcr_calls": fcr_calls,
        "fcr_rate": round(fcr_rate, 2),
        "top_tags": tags_df['tag_list'].value_counts().reset_index(name='Frequência'),
        "reincidence_table": tag_reincidence,
        "order_reincidence": order_reincidence
    }

def calculate_csat_metrics(evaluations_list):
    # Dicionário de mapeamento das notas
    csat_map = {
        5: "🤩 Muito satisfeito",
        4: "😁 Satisfeito",
        3: "😐 Neutro",
        2: "☹️ Insatisfeito",
        1: "😡 Muito insatisfeito"
    }

    if not evaluations_list:
        empty_dist = pd.DataFrame([
            {"Nota": k, "Categoria": v, "Quantidade": 0, "Proporção": 0.0, "Texto": "0.0% (0)"}
            for k, v in csat_map.items()
        ])
        return {
            "avg": 0.0, 
            "positive_percentage": 0.0,
            "count": 0, 
            "dist": empty_dist.sort_values('Nota', ascending=True)
        }
    
    df = pd.DataFrame(evaluations_list, columns=['nota'])
    avg = df['nota'].mean()
    total = len(df)
    counts = df['nota'].value_counts().to_dict()

    # Cálculo da porcentagem de CSAT Positivo (Notas 4 e 5)
    positive_count = counts.get(4, 0) + counts.get(5, 0)
    positive_percentage = (positive_count / total * 100) if total > 0 else 0.0

    dist_data = []
    for nota, categoria in csat_map.items():
        qtd = counts.get(nota, 0)
        prop = (qtd / total * 100) if total > 0 else 0
        dist_data.append({
            "Nota": nota,
            "Categoria": categoria,
            "Quantidade": qtd,
            "Proporção": prop,
            "Texto": f"{prop:.1f}% ({qtd})"
        })
        
    dist = pd.DataFrame(dist_data)
    
    # Ordena crescente (1 a 5) para que no gráfico Plotly a nota 5 fique no topo
    dist = dist.sort_values('Nota', ascending=True)
    
    return {
        "avg": round(avg, 2),
        "positive_percentage": round(positive_percentage, 1),
        "count": total,
        "dist": dist
    }
