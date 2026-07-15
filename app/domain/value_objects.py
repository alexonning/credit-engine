"""Value Objects do domínio: imutáveis, autovalidados, comparados por valor."""
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class Documento(BaseModel):
    """CPF ou CNPJ validado por dígito verificador."""
    model_config = ConfigDict(frozen=True)

    numero: str

    @field_validator("numero")
    @classmethod
    def _normaliza_e_valida(cls, v: str) -> str:
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) == 11:
            if not _cpf_valido(digits):
                raise ValueError("CPF inválido")
        elif len(digits) == 14:
            if not _cnpj_valido(digits):
                raise ValueError("CNPJ inválido")
        else:
            raise ValueError("Documento deve ser CPF (11 dígitos) ou CNPJ (14 dígitos)")
        return digits

    @property
    def tipo(self) -> str:
        return "CPF" if len(self.numero) == 11 else "CNPJ"


class Dinheiro(BaseModel):
    """Valor monetário em BRL com precisão decimal."""
    model_config = ConfigDict(frozen=True)

    valor: Decimal
    moeda: str = "BRL"

    @field_validator("valor")
    @classmethod
    def _nao_negativo(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Valor monetário não pode ser negativo")
        return v.quantize(Decimal("0.01"))


class Score(BaseModel):
    """Score de crédito normalizado (0–1000)."""
    model_config = ConfigDict(frozen=True)

    valor: int
    fonte: str

    @field_validator("valor")
    @classmethod
    def _faixa(cls, v: int) -> int:
        if not 0 <= v <= 1000:
            raise ValueError("Score deve estar entre 0 e 1000")
        return v


class Vigencia(BaseModel):
    """Período de vigência de uma regra ou política (ISO date strings)."""
    model_config = ConfigDict(frozen=True)

    inicio: str
    fim: str | None = None

    @model_validator(mode="after")
    def _fim_apos_inicio(self) -> Self:
        if self.fim is not None and self.fim < self.inicio:
            raise ValueError("Fim da vigência não pode ser anterior ao início")
        return self


def _cpf_valido(cpf: str) -> bool:
    if cpf == cpf[0] * 11:
        return False
    for i in (9, 10):
        soma = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
        dig = (soma * 10) % 11
        if dig == 10:
            dig = 0
        if dig != int(cpf[i]):
            return False
    return True


def _cnpj_valido(cnpj: str) -> bool:
    if cnpj == cnpj[0] * 14:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, *pesos1]
    for pesos, pos in ((pesos1, 12), (pesos2, 13)):
        soma = sum(int(cnpj[i]) * p for i, p in enumerate(pesos))
        resto = soma % 11
        dig = 0 if resto < 2 else 11 - resto
        if dig != int(cnpj[pos]):
            return False
    return True
