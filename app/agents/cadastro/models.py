"""Modelos de entrada/saída do CadastroAgent."""
from pydantic import BaseModel, Field, model_validator
from typing import Self


class CadastroOutput(BaseModel):
    """Saída estruturada do CadastroAgent — nunca texto livre."""
    status: str = Field(pattern="^(OK|PENDENTE)$")
    score_cadastral: int = Field(ge=0, le=100)
    pendencias: list[str] = Field(default_factory=list, max_length=6)
    observacoes: list[str] = Field(default_factory=list)
    inconsistencias: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _coerencia_status(self) -> Self:
        if self.pendencias and self.status != "PENDENTE":
            raise ValueError("Status deve ser PENDENTE quando há pendências")
        return self
