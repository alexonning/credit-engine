# Credit Analysis Engine

Agente de IA multi-agente para **análise de crédito**, com orquestração via
**LangGraph**, regras determinísticas desacopladas do LLM, API **FastAPI**,
integração com **Azure OpenAI**, **PostgreSQL**, **Redis**, auditoria e Docker.

## Arquitetura

```
                          FastAPI  (/api/v1/credit/analyze)
                                     |
                          build_context()  -> variáveis planas
                                     |
                        LangGraph Orchestrator
                                     |
                                cadastro
                                     | (fan-out paralelo)
        +----------------+----------------+----------------+
        |                |                |                |
 regras_sistemicas  regras_internas   concessao         produto
        |                |                |                |
        +----------------+--- decision ---+----------------+   (fan-in)
                                     |  (Decision Engine determinístico)
                                negociacao
                                     |
                             explicabilidade
                                     |
                          CreditResponse (decisão + oferta + explicação)
```

### Princípio central: LLM desacoplado da decisão
- O **Rule Engine** (`app/engine/rule_engine.py`) avalia regras declaradas em
  YAML (`app/engine/rules/*.yaml`) com um avaliador de expressões **seguro**
  (sem `eval` do Python). A decisão é 100% reproduzível e auditável.
- O **LLM** (Azure OpenAI) é usado **apenas** para redigir o racional/explicação
  em linguagem natural sobre fatos já calculados. Nunca altera a decisão.

### Categorias de regras
| Categoria    | Arquivo            | Agente               |
|--------------|--------------------|----------------------|
| Sistêmica    | `sistemicas.yaml`  | `regras_sistemicas`  |
| Interna      | `internas.yaml`    | `regras_internas`    |
| Concessão    | `concessao.yaml`   | `concessao`          |
| Produto      | `produtos.yaml`    | `produto`            |

Produtos suportados de exemplo: `CDC`, `CONSIGNADO`, `CARTAO`, `HOME_EQUITY`.

## Como rodar

### 1) Local (sem Docker)
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # LLM_USE_STUB=true já vem ligado (sem custo)
uvicorn app.main:app --reload
```
Acesse a documentação interativa em http://localhost:8000/docs

### 2) Docker Compose (API + Postgres + Redis)
```bash
cp .env.example .env
docker compose up --build
```

### 3) Testes
```bash
pytest -q
```

## Exemplo de requisição

```bash
curl -X POST http://localhost:8000/api/v1/credit/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "applicant": {
      "document": "12345678900",
      "name": "Maria Silva",
      "monthly_income": "6000",
      "existing_debt": "300",
      "credit_score": 720,
      "employment_status": "employed"
    },
    "product": {"product_code": "CDC", "amount": "20000", "term_months": 24}
  }'
```

Resposta (resumo):
```json
{
  "decision": "APPROVED",
  "score": 0.98,
  "approved_amount": "20000",
  "agent_results": [ ... ],
  "offer": { "approved_amount": "20000", "term_months": 24, "interest_rate": 0.18 },
  "explanation": "Seu crédito foi APROVADO ..."
}
```

## Streaming da explicação (SSE)

`POST /api/v1/credit/analyze/stream` faz a **mesma análise**, mas responde em
**Server-Sent Events**: a decisão (determinística e rápida) chega imediatamente
e a explicação do LLM é transmitida **token a token**. Ideal para UI em tempo real.

Sequência de eventos:
```
event: decision      -> {decision, score, approved_amount, offer, agent_results}  (imediato)
event: explanation   -> {"delta": "Seu"}      (token a token)
event: explanation   -> {"delta": " crédito"}
...
event: done          -> {request_id}
```

```bash
curl -N -X POST http://localhost:8000/api/v1/credit/analyze/stream \
  -H "Content-Type: application/json" \
  -d '{"applicant":{"document":"123","name":"Maria","monthly_income":"6000","credit_score":720},
       "product":{"product_code":"CDC","amount":"20000","term_months":24}}'
```

Consumo no browser:
```js
const resp = await fetch("/api/v1/credit/analyze/stream", {
  method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(payload),
});
const reader = resp.body.getReader();
// ... parse dos frames SSE, atualizando a UI a cada delta ...
```

Por que funciona bem aqui: a **decisão** sai do Rule/Decision Engine em
milissegundos e é enviada primeiro; só a **redação** (LLM) é streamada depois —
graças à separação LLM ↔ decisão.

## Escolher o provedor de LLM (Azure OpenAI ou Claude)

O LLM é usado **apenas** para redigir a explicação em linguagem natural — a
decisão continua determinística. Há três modos, controlados por `.env`:

| `LLM_USE_STUB` | `LLM_PROVIDER` | Comportamento |
|----------------|----------------|---------------|
| `true` (padrão) | —              | Stub determinístico, sem credenciais nem custo (dev/testes) |
| `false`         | `azure`        | **Azure OpenAI** |
| `false`         | `anthropic`    | **API da Anthropic (Claude)** |

### Azure OpenAI
```env
LLM_USE_STUB=false
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://sua-instancia.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### Claude (para quando não for possível usar a Azure)
```env
LLM_USE_STUB=false
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-opus-4-8
```

Ambos os provedores implementam a mesma interface (`complete` + `stream`), então
tanto `/analyze` quanto `/analyze/stream` funcionam sem qualquer outra mudança —
basta trocar o `.env`. O cliente Claude usa o SDK oficial `anthropic`
(`client.messages.create` / `client.messages.stream`); se `ANTHROPIC_API_KEY`
ficar em branco, o SDK resolve a credencial do ambiente automaticamente.

## Estrutura do projeto
```
app/
  api/            rotas FastAPI
  agents/         agentes especializados (cadastro, sistêmicas, internas,
                  concessão, produto, explicabilidade, negociação)
  engine/         rule engine + decision engine + regras YAML + contexto
  orchestrator/   grafo LangGraph + estado
  llm/            cliente Azure OpenAI + stub determinístico
  db/             modelos e sessão SQLAlchemy
  cache/          cliente Redis
  core/           logging estruturado + auditoria
  services/       serviço de aplicação (cache + persistência + auditoria)
  config.py       configuração via pydantic-settings
tests/            testes unitários e de integração
```

## Como estender
- **Nova regra**: adicione um item no YAML da categoria — sem tocar em código.
- **Novo produto**: use `product_scope: ["MEU_PRODUTO"]` nas regras de produto.
- **Nova categoria/agente**: crie o YAML, um agente que herda de `BaseAgent` e
  registre o nó no grafo (`app/orchestrator/graph.py`).
