"""Enumerações do domínio de análise de crédito."""
from enum import StrEnum


class DecisionOutcome(StrEnum):
    APROVADO = "APROVADO"
    REPROVADO = "REPROVADO"
    APROVADO_COM_RESTRICOES = "APROVADO_COM_RESTRICOES"
    SOLICITAR_DOCUMENTACAO = "SOLICITAR_DOCUMENTACAO"
    SOLICITAR_GARANTIAS = "SOLICITAR_GARANTIAS"
    CONTRAPROPOSTA = "CONTRAPROPOSTA"


class RuleAction(StrEnum):
    """Ação aplicada quando uma regra é violada."""
    BLOQUEAR = "BLOQUEAR"                # reprovação imediata
    RESTRINGIR = "RESTRINGIR"            # aprovação com restrições
    EXIGIR_DOCUMENTO = "EXIGIR_DOCUMENTO"
    EXIGIR_GARANTIA = "EXIGIR_GARANTIA"
    ALERTAR = "ALERTAR"                  # apenas registra para o comitê


class RuleCriticality(StrEnum):
    BAIXA = "BAIXA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    CRITICA = "CRITICA"


class RuleType(StrEnum):
    SISTEMICA = "SISTEMICA"   # regulatória / bacen / bureaus
    INTERNA = "INTERNA"       # política interna da cooperativa
    PRODUTO = "PRODUTO"       # elegibilidade e limites do produto
    COMPLIANCE = "COMPLIANCE" # PLD/FT, sanções, PEP


class AgentStatus(StrEnum):
    OK = "OK"
    PENDENTE = "PENDENTE"
    REPROVADO = "REPROVADO"
    ERRO = "ERRO"
