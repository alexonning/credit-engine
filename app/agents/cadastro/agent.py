"""CadastroAgent: avaliação qualitativa dos dados cadastrais via LLM."""
import json
from typing import Any

from app.agents.base import BaseAgent
from app.agents.cadastro.models import CadastroOutput
from app.agents.cadastro.validators import campos_ausentes
from app.utils.masking import mask_pii


class CadastroAgent(BaseAgent[CadastroOutput]):
    nome = "cadastro"
    output_model = CadastroOutput
    tier_principal = "gpt-4.1-mini"
    tier_fallback = "gpt-4.1"
    prompt_version = "1.0.0"

    def montar_user_prompt(self, contexto: dict[str, Any]) -> str:
        template = self._carregar_prompt("user_prompt.md")
        cliente: dict[str, Any] = contexto["cliente"]
        proposta: dict[str, Any] = contexto["proposta"]
        ausentes = campos_ausentes(cliente)
        return template.format(
            dados_cliente=mask_pii(json.dumps(cliente, ensure_ascii=False, default=str)),
            dados_proposta=json.dumps(proposta, ensure_ascii=False, default=str),
            campos_ausentes=json.dumps(ausentes, ensure_ascii=False) if ausentes else "Nenhum",
        )
