"""Testes de value objects (validação de documentos e dinheiro)."""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.domain.value_objects import Dinheiro, Documento, Score


def test_cpf_valido() -> None:
    doc = Documento(numero="529.982.247-25")
    assert doc.numero == "52998224725"
    assert doc.tipo == "CPF"


def test_cpf_invalido() -> None:
    with pytest.raises(ValidationError, match="CPF inválido"):
        Documento(numero="111.111.111-11")


def test_cnpj_valido() -> None:
    doc = Documento(numero="11.222.333/0001-81")
    assert doc.tipo == "CNPJ"


def test_dinheiro_negativo_rejeitado() -> None:
    with pytest.raises(ValidationError):
        Dinheiro(valor=Decimal("-10"))


def test_score_fora_de_faixa() -> None:
    with pytest.raises(ValidationError):
        Score(valor=1500, fonte="bureau")
