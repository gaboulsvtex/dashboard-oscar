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

def calculate_sac_metrics(df: pd.DataFrame):
    """Calcula estatísticas de chamados, reincidência, FCR e Pedidos."""
    if df.empty:
        return {
            "total_calls": 0,
            "single_contact": 0,
            "recurrent_clients": 0,
            "fcr_rate": 0.0,
            "top_tags": pd.DataFrame(),
            "reincidence_table": pd.DataFrame()
        }

    # Total de chamados (cada linha na API v2 é um atendimento humano)
    total_calls = len(df) #
    
    # Estatísticas por URN (Identificador do contato)
    urn_stats = df['urn'].value_counts()
    
    # "Atendimentos Únicos" são chamados de clientes que apareceram apenas 1 vez
    single_contacts = urn_stats[urn_stats == 1].count()
    
    # Cálculo do FCR baseado na sua regra: (Chamados não reincidentes / Total de chamados)
    fcr_rate = (single_contacts / total_calls * 100) if total_calls > 0 else 0.0
    
    # Processamento de tags
    tags_df = df.explode('tag_list')
    
    # Tabela de reincidência
    group_cols = ['urn', 'tag_list', 'sector_name'] if 'sector_name' in tags_df.columns else ['urn', 'tag_list']
    tag_reincidence = tags_df.groupby(group_cols).size().reset_index(name='qtd_salas')
    tag_reincidence = tag_reincidence[tag_reincidence['qtd_salas'] > 1].sort_values(by='qtd_salas', ascending=False)


    # ----- Reincidencia por Pedido ----
    # 1. Criar coluna de ID de Pedido
    df['order_id'] = df['protocol'].apply(extract_order_id)
    
    # 2. Filtrar apenas registros que possuem pedido identificado
    df_orders = df[df['order_id'].notna()].copy()
    
    # 3. Agrupar por Pedido e listar os protocolos únicos e quantidade
    order_reincidence = df_orders.groupby('order_id').agg({
        'protocol': lambda x: list(set(x)),
        'sector_name': lambda x: list(set([s for s in x if s])), # Remove vazios e duplicados
        'uuid': 'count'
    }).reset_index()
    
    order_reincidence.columns = ['ID do Pedido', 'Protocolos Relacionados','Setor', 'Qtd Tickets']
    
    # 4. Filtrar apenas pedidos com MAIS de um ticket (reincidência)
    order_reincidence = order_reincidence[order_reincidence['Qtd Tickets'] > 1].sort_values(by='Qtd Tickets', ascending=False)

    return {
        "total_calls": total_calls,
        "single_contact": single_contacts,
        "recurrent_clients": urn_stats[urn_stats > 1].count(),
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
        return {"avg": 0.0, "count": 0, "dist": empty_dist.sort_values('Nota', ascending=True)}
    
    df = pd.DataFrame(evaluations_list, columns=['nota'])
    avg = df['nota'].mean()
    total = len(df)
    counts = df['nota'].value_counts().to_dict()

    dist_data = []
    for nota, categoria in csat_map.items():
        qtd = counts.get(nota, 0)
        prop = (qtd / total * 100) if total > 0 else 0
        dist_data.append({
            "Nota": nota,
            "Categoria": categoria,
            "Quantidade": qtd,
            "Proporção": prop,
            "Texto": f"{prop:.1f}% ({qtd})" # Formato visual do rótulo
        })
        
    dist = pd.DataFrame(dist_data)
    
    # Ordena crescente (1 a 5) para que no gráfico Plotly a nota 5 fique no topo
    dist = dist.sort_values('Nota', ascending=True)
    
    return {
        "avg": round(avg, 2),
        "count": len(df),
        "dist": dist
    }