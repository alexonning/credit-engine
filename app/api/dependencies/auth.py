"""Autenticação JWT (OAuth2 password bearer).

Em produção, o emissor é o Azure AD (validação por JWKS); esta implementação
valida tokens HS256 emitidos internamente e mantém o mesmo contrato de claims.
"""
from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config.settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


class UsuarioAtual(BaseModel):
    sub: str
    escopos: list[str]


def criar_token(sub: str, escopos: list[str]) -> str:
    settings = get_settings()
    payload = {
        "sub": sub,
        "scopes": escopos,
        "exp": datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def usuario_atual(token: str = Depends(oauth2_scheme)) -> UsuarioAtual:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sem subject")
    return UsuarioAtual(sub=sub, escopos=list(payload.get("scopes", [])))
