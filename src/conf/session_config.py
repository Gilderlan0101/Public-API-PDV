# src/core/session_config.py
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from fastapi_sessions.backends.implementations import InMemoryBackend
from fastapi_sessions.frontends.implementations import (
    CookieParameters,
    SessionCookie,
)
from fastapi_sessions.session_verifier import SessionVerifier
from pydantic import BaseModel


class SessionData(BaseModel):
    user_id: Optional[int] = None
    empresa_id: Optional[int] = None
    tipo: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    employee_id: Optional[int] = None
    membro_id: Optional[int] = None
    additional_data: Dict[str, Any] = {}


# Configuração do backend de sessão
backend = InMemoryBackend[UUID, SessionData]()

# Configuração do cookie
cookie_params = CookieParameters(
    max_age=28800,
    path='/',
    domain=None,
    secure=False,
    httponly=True,
    samesite='lax',  # 8 horas  # True em produção com HTTPS
)

cookie = SessionCookie(
    cookie_name='pdv_session',
    identifier='general_verifier',
    auto_error=True,
    secret_key='sua_chave_secreta_super_segura_aqui_2024_pdv',
    cookie_params=cookie_params,
)


class BasicVerifier(SessionVerifier[UUID, SessionData]):
    def __init__(
        self,
        *,
        identifier: str,
        auto_error: bool,
        backend: InMemoryBackend[UUID, SessionData],
        auth_http_exception: Exception,
    ):
        self._identifier = identifier
        self._auto_error = auto_error
        self._backend = backend
        self._auth_http_exception = auth_http_exception

    @property
    def identifier(self):
        return self._identifier

    @property
    def backend(self):
        return self._backend

    @property
    def auto_error(self):
        return self._auto_error

    @property
    def auth_http_exception(self):
        return self._auth_http_exception

    def verify_session(self, model: SessionData) -> bool:
        """Returns `True` if the session exists and is valid"""
        return True


verifier = BasicVerifier(
    identifier='general_verifier',
    auto_error=True,
    backend=backend,
    auth_http_exception=HTTPException(
        status_code=403, detail='Sessão inválida'
    ),
)
