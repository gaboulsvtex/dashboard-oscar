import requests
import pandas as pd
import streamlit as st
import datetime

class WeniChatsEngineClient:
    def __init__(self, token: str):
        # 1. Limpamos espaços e garantimos que o prefixo Bearer esteja correto
        clean_token = token.strip()
        if not clean_token.startswith("Bearer "):
            clean_token = f"Bearer {clean_token}"
            
        # 2. Garante a barra final na URL para evitar redirecionamentos que limpam o header
        self.base_url = "https://chats-engine.weni.ai/v2/external/rooms_metrics/"
        
        self.headers = {
            "Authorization": clean_token,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    @st.cache_data(show_spinner="Consultando API Weni...", ttl=600)
    def fetch_metrics(_self, start_date: datetime.date, end_date: datetime.date):
        params = {
            "ended_at__gte": start_date.strftime("%Y-%m-%dT00:00:00Z"),
            "ended_at__lte": end_date.strftime("%Y-%m-%dT23:59:59Z"),
            "ordering": "-created_on",
            "page_size": 100
        }
        
        all_results = []
        next_url = _self.base_url
        
        try:
            while next_url:
                response = requests.get(
                    next_url, 
                    headers=_self.headers, 
                    params=params if next_url == _self.base_url else None,
                    timeout=30,
                    allow_redirects=True
                )
                if response.status_code == 401:
                    print(f"DEBUG: Falha com o Token: {_self.headers['Authorization'][:15]}...")
                response.raise_for_status()
                data = response.json()
                
                all_results.extend(data.get("results", []))
                next_url = data.get("next") 
            
            if not all_results:
                return pd.DataFrame()
            
            return _self._process_raw_data(all_results)
            
        except requests.exceptions.RequestException as e:
            st.error(f"Erro de Conexão: {e}")
            return pd.DataFrame()

    def _process_raw_data(self, raw_data):
        df = pd.json_normalize(raw_data)
        
        # Garantir conversão de datas
        df['created_on'] = pd.to_datetime(df['created_on'])
        
        # Tratamento seguro de tags (previne erro se a coluna não existir)
        if 'tags' in df.columns:
            df['tag_list'] = df['tags'].apply(
                lambda x: [tag['name'] for tag in x] if isinstance(x, list) else []
            )
        else:
            df['tag_list'] = [[] for _ in range(len(df))]

        # Setor: API retorna objeto aninhado sector com name
        if 'sector.name' in df.columns:
            df['sector_name'] = df['sector.name'].fillna('').astype(str)
        else:
            df['sector_name'] = ''

        return df

class WeniSupervisorClient:
    def __init__(self, project_uuid: str, api_key: str):
        self.project_uuid = project_uuid
        self.base_url = f"https://nexus.weni.ai/api/public/{project_uuid}/supervisor/conversations"
        self.headers = {"Authorization": f"ApiKey {api_key.strip()}", "Accept": "application/json"}

    @st.cache_data(ttl=600)
    def fetch_ai_conversations(_self, start_date, end_date):
        params = {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "page_size": 50
        }
        all_results = []
        # Para simplificação, pegamos a primeira página e o resumo de status
        try:
            response = requests.get(_self.base_url, headers=_self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json() # Retorna o dicionário completo com status_summary e results
        except Exception as e:
            st.error(f"Erro IA ({_self.project_uuid}): {e}")
            return None