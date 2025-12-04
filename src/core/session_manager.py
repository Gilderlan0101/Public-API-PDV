# src/core/session_manager.py
import json
import os
import secrets
from typing import Any, Dict, Optional

import redis
from dotenv import load_dotenv
from fastapi import HTTPException, Request, Response

load_dotenv()


class RedisSessionManager:
    def __init__(
        self,
        redis_url: str = os.getenv('CACHE_REDIS', 'redis://localhost:6379'),
    ):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.expire_time = 8 * 60 * 60  # 8 horas em segundos

    def create_session(self, response: Response, data: Dict[str, Any]) -> str:
        """Cria uma nova sessão no Redis"""
        session_id = secrets.token_urlsafe(32)

        self.redis.setex(
            f'session:{session_id}', self.expire_time, json.dumps(data)
        )

        # Configura o cookie
        response.set_cookie(
            key='pdv_session',
            value=session_id,
            max_age=self.expire_time,
            httponly=True,
            secure=True,
            samesite='lax',  # True em produção
        )

        return session_id

    def get_session(self, request: Request) -> Optional[Dict[str, Any]]:
        """Recupera os dados da sessão do Redis"""
        session_id = request.cookies.get('pdv_session')
        if not session_id:
            return None

        session_data = self.redis.get(f'session:{session_id}')
        if not session_data:
            return None

        return json.loads(session_data)

    def update_session(self, request: Request, data: Dict[str, Any]) -> bool:
        """Atualiza os dados da sessão no Redis"""
        session_id = request.cookies.get('pdv_session')
        if not session_id:
            return False

        # Recupera dados atuais
        current_data = self.get_session(request)
        if not current_data:
            return False

        # Atualiza e salva
        current_data.update(data)

        self.redis.setex(
            f'session:{session_id}', self.expire_time, json.dumps(current_data)
        )

        return True

    def delete_session(self, request: Request, response: Response) -> bool:
        """Remove a sessão do Redis"""
        session_id = request.cookies.get('pdv_session')
        if not session_id:
            return False

        self.redis.delete(f'session:{session_id}')
        response.delete_cookie('pdv_session')
        return True

    def extend_session(self, request: Request) -> bool:
        """Estende o tempo da sessão"""
        session_id = request.cookies.get('pdv_session')
        if not session_id:
            return False

        return bool(
            self.redis.expire(f'session:{session_id}', self.expire_time)
        )


# Instância global
session_manager = RedisSessionManager()


# Dependência para FastAPI
async def get_session(request: Request) -> Dict[str, Any]:
    """Dependência para obter a sessão atual"""
    session = session_manager.get_session(request)
    if not session:
        raise HTTPException(
            status_code=401,
            detail='Sessão não encontrada. Faça login novamente.',
        )
    return session
