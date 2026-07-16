"""Trilha de auditoria: persiste cada decisao de credito para rastreabilidade."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import AuditLog

logger = get_logger("audit")


def record_audit(
    db: Session | None,
    *,
    request_id: str,
    stage: str,
    payload: dict[str, Any],
    decision: str | None = None,
) -> None:
    """Grava um evento de auditoria. Sempre loga; persiste se houver sessao de DB."""
    logger.info("audit_event", request_id=request_id, stage=stage, decision=decision)

    if db is None:
        return

    try:
        entry = AuditLog(
            request_id=request_id,
            stage=stage,
            decision=decision,
            payload=json.dumps(payload, default=str, ensure_ascii=False),
        )
        db.add(entry)
        db.commit()
    except Exception as exc:  # noqa: BLE001 - auditoria nunca deve quebrar o fluxo
        logger.warning("audit_persist_failed", error=str(exc))
        db.rollback()
