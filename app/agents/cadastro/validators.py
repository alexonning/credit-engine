"""Pré-validação determinística do cadastro (antes do LLM).

Campos obrigatórios ausentes são detectados por código, não por modelo —
o LLM recebe essa lista pronta e foca na análise qualitativa.
"""
from typing import Any

CAMPOS_OBRIGATORIOS: tuple[str, ...] = (
    "nome",
    "documento",
    "renda_mensal",
    "ocupacao",
    "endereco",
    "telefone",
)


def campos_ausentes(dados_cliente: dict[str, Any]) -> list[str]:
    ausentes: list[str] = []
    for campo in CAMPOS_OBRIGATORIOS:
        valor = dados_cliente.get(campo)
        if valor is None or (isinstance(valor, str) and not valor.strip()):
            ausentes.append(campo)
    return ausentes
