"""Mascaramento de dados pessoais (LGPD) para logs e auditoria."""
import re

_CPF_RE = re.compile(r"\b(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})\b")
_CNPJ_RE = re.compile(r"\b(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})\b")
_EMAIL_RE = re.compile(r"\b([A-Za-z0-9._%+-]{1,2})[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+)\b")


def mask_document(value: str) -> str:
    """Mascara CPF/CNPJ mantendo apenas os últimos dígitos visíveis."""
    value = _CNPJ_RE.sub(r"**.***.***/****-\5", value)
    value = _CPF_RE.sub(r"***.***.***-\4", value)
    return value


def mask_email(value: str) -> str:
    return _EMAIL_RE.sub(r"\1***\2", value)


def mask_pii(value: str) -> str:
    """Aplica todas as regras de mascaramento em uma string."""
    return mask_email(mask_document(value))
