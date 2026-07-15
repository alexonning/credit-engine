"""Testes do Decision Engine: precedência e consolidação."""
from app.decision_engine.engine import DecisionEngine, ParecerAgente
from app.domain.enums import AgentStatus, DecisionOutcome, RuleAction, RuleCriticality
from app.rule_engine.models import ResultadoRegra


def _resultado(acao: RuleAction, disparou: bool = True, **overrides: object) -> ResultadoRegra:
    base: dict = {
        "codigo": "TST-001",
        "nome": "Teste",
        "versao": 1,
        "disparou": disparou,
        "acao": acao,
        "criticidade": RuleCriticality.ALTA,
        "prioridade": 100,
        "explicacao": "Explicação da regra",
    }
    base.update(overrides)
    return ResultadoRegra(**base)


def _parecer_ok() -> ParecerAgente:
    return ParecerAgente(agente="cadastro", status=AgentStatus.OK)


def test_bloqueio_tem_precedencia_absoluta() -> None:
    decisao = DecisionEngine().decidir(
        pareceres=[_parecer_ok()],
        resultados_regras=[
            _resultado(RuleAction.BLOQUEAR),
            _resultado(RuleAction.RESTRINGIR, codigo="TST-002"),
        ],
    )
    assert decisao.resultado == DecisionOutcome.REPROVADO
    assert "TST-001:v1" in decisao.regras_disparadas


def test_garantia_antes_de_documentacao() -> None:
    decisao = DecisionEngine().decidir(
        pareceres=[_parecer_ok()],
        resultados_regras=[
            _resultado(RuleAction.EXIGIR_GARANTIA, garantia_exigida="Avalista"),
            _resultado(RuleAction.EXIGIR_DOCUMENTO, codigo="TST-002",
                       documento_exigido="Comprovante de renda"),
        ],
    )
    assert decisao.resultado == DecisionOutcome.SOLICITAR_GARANTIAS
    assert decisao.garantias_exigidas == ["Avalista"]


def test_pendencia_de_agente_gera_solicitacao_de_documentos() -> None:
    parecer = ParecerAgente(
        agente="cadastro",
        status=AgentStatus.PENDENTE,
        motivos=["Renda incompatível com ocupação"],
        documentos_pendentes=["Comprovante de renda"],
    )
    decisao = DecisionEngine().decidir(pareceres=[parecer], resultados_regras=[])
    assert decisao.resultado == DecisionOutcome.SOLICITAR_DOCUMENTACAO
    assert decisao.documentos_pendentes == ["Comprovante de renda"]


def test_restricao_gera_aprovado_com_restricoes() -> None:
    decisao = DecisionEngine().decidir(
        pareceres=[_parecer_ok()],
        resultados_regras=[_resultado(RuleAction.RESTRINGIR)],
    )
    assert decisao.resultado == DecisionOutcome.APROVADO_COM_RESTRICOES
    assert decisao.permite_contraproposta is True


def test_sem_regras_disparadas_aprova() -> None:
    decisao = DecisionEngine().decidir(
        pareceres=[_parecer_ok()],
        resultados_regras=[_resultado(RuleAction.BLOQUEAR, disparou=False)],
    )
    assert decisao.resultado == DecisionOutcome.APROVADO


def test_erro_de_agente_encaminha_para_analise_manual() -> None:
    parecer = ParecerAgente(agente="cadastro", status=AgentStatus.ERRO,
                            motivos=["Timeout no LLM"])
    decisao = DecisionEngine().decidir(pareceres=[parecer], resultados_regras=[])
    assert decisao.resultado == DecisionOutcome.SOLICITAR_DOCUMENTACAO
