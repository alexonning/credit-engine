# Arquitetura

## Visão geral

```
HTTP (FastAPI) ──► Orquestrador (LangGraph)
                      │
        ┌─────────────┼──────────────┐
        ▼             ▼              ▼
   Agentes IA    Rule Engine   Decision Engine
 (Azure OpenAI) (determinístico)(determinístico)
        │             │              │
        └────────► PostgreSQL ◄──────┘
                  (análises, regras versionadas,
                   execuções, auditoria)
                       ▲
                     Redis
              (estado, cache, checkpoint)
```

## Camadas (Clean Architecture / Hexagonal)

| Camada | Diretório | Depende de |
|---|---|---|
| Domain | `app/domain` | nada |
| Application | `app/agents/*/service.py`, `orchestrator`, `decision_engine`, `rule_engine` | Domain |
| Infrastructure | `app/database`, `app/repositories`, `app/services/llm`, `app/memory` | Application/Domain |
| Presentation | `app/api`, `app/schemas` | Application |

Regra de dependência: setas sempre apontam para dentro. O domínio não conhece
FastAPI, SQLAlchemy nem LangChain.

## Fluxo da análise

1. `POST /api/v1/credit-analysis` (JWT obrigatório).
2. Nó `validar`: valida a presença das seções obrigatórias do contexto.
3. Nó `cadastro`: CadastroAgent (LLM, saída estruturada `CadastroOutput`).
4. Nó `regras`: Rule Engine avalia todas as regras vigentes do produto.
5. Nó `decisao`: Decision Engine consolida com precedência explícita.
6. Nó `explicacao`: gera texto auditável da decisão.
7. Persistência da análise + trilha de auditoria na mesma transação (UoW).

## Contratos-chave

- Agente → `ParecerAgente {agente, status, motivos, documentos_pendentes, score_ajustado}`
- Regra → `ResultadoRegra {codigo, versao, disparou, acao, criticidade, explicacao}`
- Decisão → `DecisaoFinal {resultado, motivos, restricoes, documentos, garantias, regras_disparadas}`

Novos agentes (compliance, produto, concessão, negociação) entram como novos
nós do grafo produzindo `ParecerAgente` — o Decision Engine não muda.

## Versionamento

- **Regras**: `rules.versao_atual` + histórico completo em `rule_versions`.
  A decisão registra `codigo:vN` de cada regra disparada.
- **Prompts**: arquivos `.md` versionados por agente (`prompt_version`) e
  espelhados em `prompt_versions` para rastreabilidade em produção.

## Segurança e LGPD

- JWT/OAuth2 (Azure AD em produção via JWKS).
- Segredos via Azure Key Vault (injeção por ambiente).
- Mascaramento de CPF/CNPJ/e-mail antes de qualquer prompt ou log (`utils/masking.py`).
