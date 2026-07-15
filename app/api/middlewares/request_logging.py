"""Middleware de logging estruturado + correlação por request."""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.utils.logging import get_logger

logger = get_logger("http")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)
        inicio = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_erro", metodo=request.method, caminho=request.url.path)
            raise
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        duracao_ms = int((time.perf_counter() - inicio) * 1000)
        logger.info(
            "request_concluida",
            metodo=request.method,
            caminho=request.url.path,
            status=response.status_code,
            duracao_ms=duracao_ms,
        )
        response.headers["x-request-id"] = request_id
        return response
