# Documentação Técnica: Weni Chats Engine API (v2)

Esta documentação detalha o endpoint de métricas de salas externas da Weni Chats Engine, fornecendo uma visão completa dos filtros disponíveis e da estrutura de dados retornada.

- **Base URL:** `https://chats-engine.weni.ai`
- **Endpoint:** `GET /v2/external/rooms_metrics/`
- **Autenticação:** Header `Authorization: Bearer <seu_token>`

---

## 1. Parâmetros de Consulta (Query String Parameters)

Utilize estes parâmetros para filtrar, ordenar e paginar os resultados das métricas:

| Parâmetro           | Tipo        | Descrição                                                                                    |
| :------------------ | :---------- | :------------------------------------------------------------------------------------------- |
| `ordering`          | String      | Campo usado para ordenar os resultados (ex: `created_on` ou `-created_on` para descendente). |
| `search`            | String      | Termo de busca global. Pesquisa em campos como nome, URN, e-mail, etc.                       |
| `urn`               | String      | Filtra por um URN específico (ex: telefone ou e-mail do contato).                            |
| `is_active`         | String      | Filtra salas ativas. Use `'true'` ou `'false'`.                                              |
| `sector`            | UUID/String | Filtra as métricas por um setor específico.                                                  |
| `queue`             | UUID/String | Filtra as métricas por uma fila de atendimento específica.                                   |
| `created_on__gte`   | DateTime    | Filtra salas criadas **após** ou na data informada (ISO 8601).                               |
| `created_on__lte`   | DateTime    | Filtra salas criadas **antes** ou na data informada (ISO 8601).                              |
| `ended_at__gte`     | DateTime    | Filtra salas encerradas **após** ou na data informada (ISO 8601).                            |
| `ended_at__lte`     | DateTime    | Filtra salas encerradas **antes** ou na data informada (ISO 8601).                           |
| `external_ids`      | String      | Filtra por IDs externos associados aos contatos.                                             |
| `secondary_project` | UUID        | Filtra por um projeto secundário vinculado.                                                  |
| `cursor`            | String      | Valor do cursor para paginação (usado em listas extensas).                                   |
| `page_size`         | Integer     | Define a quantidade de resultados por página.                                                |

---

## 2. Estrutura da Resposta (Response Body)

A resposta segue o formato de paginação da API:

### Metadados

- **`next`** (string/null): URI para a próxima página de resultados.
- **`previous`** (string/null): URI para a página anterior.
- **`results`** (Array): Lista de objetos `ExternalRoomMetrics`. Cada item da array representa um atendimento humano.

### Objeto `results` (Campos Principais)

| Campo                            | Tipo          | Descrição                                                 |
| :------------------------------- | :------------ | :-------------------------------------------------------- |
| `uuid`                           | UUID          | ID único da entrada de métrica.                           |
| `created_on`                     | DateTime      | Data/hora de criação do atendimento.                      |
| `interaction_time`               | Integer       | **(Obrigatório)** Tempo total de interação (em segundos). |
| `ended_at`                       | DateTime/null | Data/hora de encerramento do atendimento.                 |
| `urn`                            | String/null   | URN do contato.                                           |
| `protocol`                       | String/null   | Número de protocolo.                                      |
| `user_assigned_at`               | DateTime/null | Horário da atribuição do usuário atual.                   |
| `first_user_message_sent_at`     | DateTime/null | Horário da primeira mensagem enviada por humano.          |
| `automatic_message_sent_at`      | DateTime/null | Horário do envio da mensagem automática.                  |
| `first_user_assigned_at`         | DateTime/null | Horário da primeira atribuição de agente na sala.         |
| `time_to_send_automatic_message` | Integer/null  | Tempo decorrido até a mensagem automática (segundos).     |
| `custom_fields`                  | Object/null   | Dicionário de campos customizados.                        |

### Objetos Aninhados em `results`

- **`contact`**: Contém `uuid` (UUID), `name` (String) e `external_id` (String).
- **`user`**: Contém `name` (String - Nome do Agente) e `email` (String - E-mail do Agente).
- **`tags`**: Array de objetos contendo `uuid` (UUID) e `name` (String).
- **`sector`**: Contém `uuid` (UUID) e `name` (String) do setor.

---

## 3. Exemplo da response

```json
{
  "next": "[https://chats-engine.weni.ai/v2/external-rooms-metrics/?page=2](https://chats-engine.weni.ai/api/v2/external-rooms-metrics/?page=2)",
  "previous": null,
  "results": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "created_on": "2024-05-20T10:00:00Z",
      "interaction_time": 450,
      "ended_at": "2024-05-20T10:45:00Z",
      "urn": "whatsapp:+5511999999999",
      "protocol": "PROT2024-100",
      "contact": {
        "uuid": "c0a80101-0000-0000-0000-000000000001",
        "name": "Cliente Exemplo",
        "external_id": "CRM-123"
      },
      "user": {
        "name": "Suporte Técnico",
        "email": "suporte@empresa.com"
      },
      "user_assigned_at": "2024-05-20T10:05:00Z",
      "first_user_message_sent_at": "2024-05-20T10:06:00Z",
      "tags": [{ "uuid": "tag-001", "name": "Resolvido" }],
      "automatic_message_sent_at": "2024-05-20T10:00:05Z",
      "first_user_assigned_at": "2024-05-20T10:02:00Z",
      "time_to_send_automatic_message": 5,
      "sector": {
        "uuid": "sec-999",
        "name": "Nível 1"
      },
      "custom_fields": {
        "categoria": "financeiro"
      }
    }
  ]
}
```

## 4. Exemplo de Requisição com Filtros (cURL)

```bash
curl -X GET "[https://chats-engine.weni.ai/v2/external-rooms-metrics/?project_uuid=SEU_UUID&created_on__gte=2024-01-01T00:00:00Z&ordering=-created_on&page_size=50](https://chats-engine.weni.ai/api/v2/external-rooms-metrics/?project_uuid=SEU_UUID&created_on__gte=2024-01-01T00:00:00Z&ordering=-created_on&page_size=50)" \
     -H "Authorization: Token SEU_TOKEN_AQUI" \
     -H "Accept: application/json"
## 3. Exemplo de Resposta JSON

```
