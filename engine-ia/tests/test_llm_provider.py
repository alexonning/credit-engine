"""Testes de selecao do provedor de LLM (stub / azure / anthropic)."""
from __future__ import annotations

from app.config import settings
from app.llm import azure_client
from app.llm.anthropic_client import AnthropicLLM
from app.llm.azure_client import StubLLM


def test_stub_is_used_by_default():
    azure_client.get_llm.cache_clear()
    try:
        assert isinstance(azure_client.get_llm(), StubLLM)
    finally:
        azure_client.get_llm.cache_clear()


def test_get_llm_selects_anthropic(monkeypatch):
    azure_client.get_llm.cache_clear()
    monkeypatch.setattr(settings, "llm_use_stub", False)
    monkeypatch.setattr(settings, "llm_provider", "anthropic")
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-key")
    try:
        llm = azure_client.get_llm()
        assert isinstance(llm, AnthropicLLM)
        # conformidade com o protocolo LLMClient (sem chamar a rede)
        assert callable(llm.complete)
        assert callable(llm.stream)
    finally:
        azure_client.get_llm.cache_clear()


def test_anthropic_stream_yields_deltas(monkeypatch):
    """Verifica o mapeamento do streaming da Anthropic sem tocar a rede."""
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test-key")
    llm = AnthropicLLM()

    class _FakeStream:
        text_stream = iter(["Seu ", "credito ", "foi ", "aprovado."])

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def _fake_stream(**kwargs):
        assert kwargs["system"]
        assert kwargs["messages"][0]["role"] == "user"
        return _FakeStream()

    monkeypatch.setattr(llm._client.messages, "stream", _fake_stream)

    out = "".join(llm.stream("system prompt", "user prompt"))
    assert out == "Seu credito foi aprovado."
