"""Decision Engine: consolida agentes + regras em uma decisão final auditável.

Determinístico. A precedência de decisão é:
  BLOQUEAR > EXIGIR_GARANTIA > EXIGIR_DOCUMENTO > RESTRINGIR/CONTRAPROPOSTA > APROVADO
"""
from pydantic import BaseModel, Field

from app.domain.enums import AgentStatus, DecisionOutcome, RuleAction
from app.rule_engine.models import ResultadoRegra
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ParecerAgente(BaseModel):
    """Parecer estruturado de um agente, consumido pelo Decision Engine."""
    agente: str
    status: AgentStatus
    motivos: list[str] = Field(default_factory=list)
    documentos_pendentes: list[str] = Field(default_factory=list)
    score_ajustado: int | None = None


class DecisaoFinal(BaseModel):
    resultado: DecisionOutcome
    motivos: list[str]
    restricoes: list[str]
    documentos_pendentes: list[str]
    garantias_exigidas: list[str]
    regras_disparadas: list[str]
    permite_contraproposta: bool


class DecisionEngine:
    def decidir(
        self,
        pareceres: list[ParecerAgente],
        resultados_regras: list[ResultadoRegra],
    ) -> DecisaoFinal:
        motivos: list[str] = []
        restricoes: list[str] = []
        documentos: list[str] = []
        garantias: list[str] = []
        disparadas = [r for r in resultados_regras if r.disparou]

        # 1. Falha operacional de agente → não decidir automaticamente
        agentes_erro = [p.agente for p in pareceres if p.status == AgentStatus.ERRO]
        if agentes_erro:
            motivos.append(f"Falha de processamento nos agentes: {', '.join(agentes_erro)}")
            return self._montar(DecisionOutcome.SOLICITAR_DOCUMENTACAO, motivos,
                                restricoes, documentos, garantias, disparadas, False)

        # 2. Bloqueios determinísticos (regras) têm precedência absoluta
        bloqueios = [r for r in disparadas if r.acao == RuleAction.BLOQUEAR]
        if bloqueios:
            motivos.extend(r.explicacao for r in bloqueios)
            return self._montar(DecisionOutcome.REPROVADO, motivos,
                                restricoes, documentos, garantias, disparadas, True)

        # 3. Reprovação por agente (ex.: compliance)
        agentes_reprovados = [p for p in pareceres if p.status == AgentStatus.REPROVADO]
        if agentes_reprovados:
            for p in agentes_reprovados:
                motivos.extend(p.motivos)
            return self._montar(DecisionOutcome.REPROVADO, motivos,
                                restricoes, documentos, garantias, disparadas, False)

        # 4. Garantias exigidas
        exige_garantia = [r for r in disparadas if r.acao == RuleAction.EXIGIR_GARANTIA]
        if exige_garantia:
            for r in exige_garantia:
                motivos.append(r.explicacao)
                if r.garantia_exigida:
                    garantias.append(r.garantia_exigida)
            return self._montar(DecisionOutcome.SOLICITAR_GARANTIAS, motivos,
                                restricoes, documentos, garantias, disparadas, True)

        # 5. Documentação pendente (regras + agentes, ex.: cadastro incompleto)
        exige_doc = [r for r in disparadas if r.acao == RuleAction.EXIGIR_DOCUMENTO]
        for r in exige_doc:
            motivos.append(r.explicacao)
            if r.documento_exigido:
                documentos.append(r.documento_exigido)
        for p in pareceres:
            documentos.extend(p.documentos_pendentes)
            if p.status == AgentStatus.PENDENTE:
                motivos.extend(p.motivos)
        if documentos:
            return self._montar(DecisionOutcome.SOLICITAR_DOCUMENTACAO, motivos,
                                restricoes, list(dict.fromkeys(documentos)),
                                garantias, disparadas, True)

        # 6. Restrições → aprovado com restrições
        restritivas = [r for r in disparadas if r.acao == RuleAction.RESTRINGIR]
        if restritivas:
            for r in restritivas:
                motivos.append(r.explicacao)
                restricoes.append(r.explicacao)
            return self._montar(DecisionOutcome.APROVADO_COM_RESTRICOES, motivos,
                                restricoes, documentos, garantias, disparadas, True)

        # 7. Aprovado
        alertas = [r for r in disparadas if r.acao == RuleAction.ALERTAR]
        motivos.extend(r.explicacao for r in alertas)
        motivos.append("Nenhuma regra impeditiva disparada; pareceres dos agentes favoráveis.")
        return self._montar(DecisionOutcome.APROVADO, motivos,
                            restricoes, documentos, garantias, disparadas, False)

    @staticmethod
    def _montar(
        resultado: DecisionOutcome,
        motivos: list[str],
        restricoes: list[str],
        documentos: list[str],
        garantias: list[str],
        disparadas: list[ResultadoRegra],
        permite_contraproposta: bool,
    ) -> DecisaoFinal:
        decisao = DecisaoFinal(
            resultado=resultado,
            motivos=motivos,
            restricoes=restricoes,
            documentos_pendentes=documentos,
            garantias_exigidas=garantias,
            regras_disparadas=[f"{r.codigo}:v{r.versao}" for r in disparadas],
            permite_contraproposta=permite_contraproposta,
        )
        logger.info("decisao_consolidada", resultado=resultado.value,
                    regras_disparadas=decisao.regras_disparadas)
        return decisao
