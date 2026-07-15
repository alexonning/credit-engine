# Credit Engine — Motor de Análise de Crédito com IA

Sistema de análise de crédito para cooperativa financeira, construído com
FastAPI, LangGraph, Azure OpenAI, PostgreSQL e Redis, seguindo DDD,
Clean Architecture e Arquitetura Hexagonal.

## Princípios arquiteturais

- **Rule Engine determinístico**: regras de política de crédito NUNCA passam
  pelo LLM. São parametrizadas, versionadas e persistidas em banco
  (`rules` / `rule_versions`), avaliadas por código puro e auditável.
- **Agentes com saída estruturada**: todo agente retorna um Pydantic model
  via structured output. Texto livre nunca entra no fluxo de decisão.
- **Decision Engine determinístico**: consolida pareceres + regras com
  precedência explícita (BLOQUEAR > GARANTIA > DOCUMENTO > RESTRIÇÃO > APROVADO).
- **Auditabilidade total**: cada análise registra contexto, versão de regras,
  versão de prompts, tokens, decisão e explicação.

## Subir o ambiente

```bash
cp .env.example .env   # preencha as credenciais do Azure OpenAI
docker compose -f docker/docker-compose.yml up --build
```

Migrações e seed:

```bash
alembic revision --autogenerate -m "initial"
alembic upgrade head
python -m scripts.seed_rules
```

## Testes

```bash
pip install -e ".[dev]"
pytest
```

## Estrutura

```
app/
  api/            # Presentation Layer (routers, middlewares, auth)
  agents/         # Agentes de IA (prompts versionados + saída estruturada)
  orchestrator/   # Grafo LangGraph do fluxo de análise
  rule_engine/    # Regras determinísticas parametrizadas
  decision_engine/# Consolidação final auditável
  domain/         # Entities, Value Objects, Enums (núcleo puro)
  database/       # ORM SQLAlchemy 2.0 + Unit of Work
  repositories/   # Repository Pattern
  services/llm/   # Fábrica Azure OpenAI (retry, fallback, tokens)
  memory/         # Estado de workflow em Redis
  schemas/        # Contratos da API
  utils/          # Logging estruturado, mascaramento LGPD
```

## Roadmap de fases

- **Fase 1 (este repositório)**: fundação executável — domínio, Rule Engine,
  Decision Engine, CadastroAgent completo, orquestrador, API, persistência,
  auditoria, testes.
- **Fase 2**: RegraSistemicaAgent, RegraInternaAgent, ProdutoAgent (cálculo
  Price/SAC com parâmetros do produto), ComplianceAgent (PLD/FT, PEP, sanções).
- **Fase 3**: ConcessaoAgent, ExplicacaoAgent (LLM), NegociacaoAgent
  (contraproposta), checkpointing LangGraph em Redis.
- **Fase 4**: OpenTelemetry → Azure Monitor, Azure AD (JWKS), Key Vault,
  testes de contrato e carga.
