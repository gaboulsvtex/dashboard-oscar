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
        self.api_key = api_key

    def fetch_ai_conversations(self, start_date, end_date):
        # Chama a função cacheadada passando as credenciais explicitamente
        return fetch_cached_ai_conversations(self.project_uuid, self.api_key, start_date, end_date)

# A função de cache fora da classe, obrigando o Streamlit 
# a criar um cache separado para CADA project_uuid e data.
@st.cache_data(ttl=600)
def fetch_cached_ai_conversations(project_uuid, api_key, start_date, end_date):
    base_url = f"https://nexus.weni.ai/api/public/{project_uuid}/supervisor/conversations"
    headers = {"Authorization": f"ApiKey {api_key.strip()}", "Accept": "application/json"}
    
    all_results = []
    total_status_summary = {}
    current_page = 1
    
    try:
        while True:
            params = {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
                "page": current_page,
                "page_size": 100
            }
            
            response = requests.get(base_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            all_results.extend(results)
            
            if current_page == 1:
                total_status_summary = data.get("status_summary", {})
            
            # Se atingiu o limite ou a página veio vazia, interrompe a paginação
            if len(all_results) >= data.get("count", 0) or not results:
                break
                
            current_page += 1

        return {
            "status_summary": total_status_summary,
            "results": all_results,
            "count": data.get("count", 0)
        }
    except Exception as e:
        st.error(f"Erro IA ({project_uuid}) na página {current_page}: {e}")
        return None

class WeniFlowsClient:
    def __init__(self, token: str, flow_uuid: str):
        self.token = token
        self.flow_uuid = flow_uuid

    def fetch_csat_data(self, start_date, end_date):
        # Chama a função cacheadada passando credenciais e o ID do fluxo explicitamente
        return fetch_cached_csat_data(self.token, self.flow_uuid, start_date, end_date)


@st.cache_data(ttl=600, show_spinner="Buscando avaliações CSAT...")
def fetch_cached_csat_data(token, flow_uuid, start_date, end_date):
    headers = {
        "Authorization": f"Token {token.strip()}",
        "Accept": "application/json"
    }
    base_url = "https://flows.weni.ai/api/v2/runs.json"
    all_evaluations = []
    
    # Inclusão do parâmetro 'flow' conforme a documentação da API
    params = {
        "flow": flow_uuid,
        "after": start_date.strftime("%Y-%m-%d"),
        "before": end_date.strftime("%Y-%m-%d"),
        "responded": "true"
    }
    
    next_url = base_url
    try:
        while next_url:
            # Se for a próxima página (next_url), os params já vêm embutidos na URL retornada pela API
            response = requests.get(
                next_url, 
                headers=headers, 
                params=params if next_url == base_url else None, 
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            
            for run in data.get("results", []):
                values = run.get("values", {})
                if "avaliacao" in values:
                    val = values["avaliacao"].get("value")
                    # Filtra apenas avaliações válidas (1 a 5)
                    if val in ["1", "2", "3", "4", "5"]:
                        all_evaluations.append(int(val))
            
            next_url = data.get("next")
            
        return all_evaluations
    except Exception as e:
        st.error(f"Erro ao buscar CSAT (Flow {flow_uuid}): {e}")
        return []


class WeniEventsClient:
    def __init__(self, token: str):
        self.token = token

    def fetch_csat_events(self, start_date, end_date):
        return fetch_cached_csat_events(self.token, start_date, end_date)

@st.cache_data(ttl=600, show_spinner="Buscando avaliações CSAT da IA...")
def fetch_cached_csat_events(token, start_date, end_date):
    headers = {
        "Authorization": f"Token {token.strip()}",
        "Content-Type": "application/json"
    }
    base_url = "https://flows.weni.ai/api/v2/events.json"
    all_evaluations = []
    
    # Formatação de datas para ISO 8601 (UTC) conforme a documentação
    date_start_str = start_date.strftime("%Y-%m-%dT00:00:00Z")
    date_end_str = end_date.strftime("%Y-%m-%dT23:59:59Z")
    
    offset = 0
    limit = 100
    buscando_dados = True # Variável de controle
    
    try:
        while buscando_dados:
            params = {
                "date_start": date_start_str,
                "date_end": date_end_str,
                "key": "weni_csat",
                "limit": limit,
                "offset": offset
            }
            
            response = requests.get(
                base_url, 
                headers=headers, 
                params=params, 
                timeout=120
            )
            response.raise_for_status()
            
            data = response.json()
        
            if not data:
                buscando_dados = False
                continue
                
            # Processamento dos dados da página atual
            for event in data:
                val = event.get("value")
                # Filtra apenas avaliações válidas (1 a 5)
                if val is not None and str(val) in ["1", "2", "3", "4", "5"]:
                    all_evaluations.append(int(val))
            
            # 2. Contar quantos objetos foram retornados
            quantidade_retornada = len(data)
            
            # 3 e 4. Regra de paginação do Offset
            if quantidade_retornada < limit:
                buscando_dados = False 
            else:
                offset += limit
                
        return all_evaluations
    except Exception as e:
        st.error(f"Erro ao buscar eventos CSAT (IA): {e}")
        return []