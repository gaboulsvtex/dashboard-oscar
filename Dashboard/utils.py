import pandas as pd

def calculate_sac_metrics(df: pd.DataFrame):
    """Calcula estatísticas de chamados, reincidência e FCR."""
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

    return {
        "total_calls": total_calls,
        "single_contact": single_contacts,
        "recurrent_clients": urn_stats[urn_stats > 1].count(),
        "fcr_rate": round(fcr_rate, 2),
        "top_tags": tags_df['tag_list'].value_counts().reset_index(name='Frequência'),
        "reincidence_table": tag_reincidence
    }