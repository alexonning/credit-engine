"""Cliente LLM para a API da Anthropic (Claude) - alternativa ao Azure OpenAI.

Usado quando o Azure OpenAI nao esta disponivel (LLM_PROVIDER=anthropic). Assim
como o AzureLLM, serve apenas para redigir o racional/explicacao em linguagem
natural sobre fatos ja calculados pelo Rule Engine - nunca decide.
"""
from __future__ import annotations

from collections.abc import Iterator

from app.config import settings

# Textos curtos de explicacao/racional nao exigem outputs longos.
_MAX_TOKENS = 500


class AnthropicLLM:
    """Wrapper fino sobre a Messages API da Anthropic (Claude)."""

    def __init__(self) -> None:
        import anthropic

        # Se anthropic_api_key estiver vazio, o SDK resolve a credencial do
        # ambiente (ANTHROPIC_API_KEY ou perfil `ant auth login`).
        self._client = (
            anthropic.Anthropic(api_key=settings.anthropic_api_key)
            if settings.anthropic_api_key
            else anthropic.Anthropic()
        )
        self._model = settings.anthropic_model

    def complete(self, system: str, user: str) -> str:
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in resp.content if block.type == "text")

    def stream(self, system: str, user: str) -> Iterator[str]:
        with self._client.messages.stream(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            yield from stream.text_stream
