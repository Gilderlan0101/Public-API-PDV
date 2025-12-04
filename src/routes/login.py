# src/routes/auth_routes.py - VERSÃO CORRIGIDA

import json
import uuid
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from src.auth.auth_jwt import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from src.auth.deps import reuseable_oauth
from src.core.cache import client
from src.logs.infos import LOGGER
from src.model.employee import Employees
from src.model.user import Usuario
from src.utils.private_infos import mask_email, mask_password


# Schema para a resposta de login
class LoginResponse(BaseModel):
    id: int
    username: str
    email: str
    empresa: str
    empresa_id: int
    tipo: str
    message: str
    access_token: str
    refresh_token: str
    token_type: str
    session_id: str


class Login:
    def __init__(self):
        self.loginRT = APIRouter(
            tags=['Autenticação'],
        )
        self._register_routes()

    # --- MÉTODOS AUXILIARES COMO ATRIBUTOS DA CLASSE ---
    async def _authenticate_admin(
        self, db_user: Usuario, password: str, username: str
    ):
        """Autentica um usuário admin"""
        if not verify_password(password, db_user.password):
            LOGGER.warning(
                f'Senha incorreta para admin: {mask_email(username)}'
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Credenciais inválidas',
            )

        return await self._generate_login_response(
            user_data=db_user, user_type='admin'
        )

    async def _authenticate_employee(
        self, db_employee: Employees, password: str, username: str
    ):
        """Autentica um funcionário"""
        # ⚠️ VERIFIQUE SE O CAMPO É 'senha' OU 'password' NO SEU MODELO
        if not verify_password(password, db_employee.senha):  # ← AJUSTE AQUI
            LOGGER.warning(f'Senha incorreta para funcionário: {username}')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Credenciais inválidas',
            )

        return await self._generate_login_response(
            user_data=db_employee, user_type='funcionario'
        )

    async def _generate_login_response(self, user_data, user_type: str):
        """Gera a resposta de login comum para ambos os tipos"""
        user_id_str = str(user_data.id)
        access_token = create_access_token(user_id_str)
        refresh_token = create_refresh_token(user_id_str)

        # Prepara dados para cache - ajuste os campos conforme seus modelos
        session_data_for_cache = {
            'id': user_data.id,
            'username': getattr(user_data, 'username', ''),
            'email': getattr(user_data, 'email', ''),
            'company_name': getattr(user_data, 'company_name', ''),
            'cnpj': getattr(user_data, 'cnpj', ''),
            'cpf': getattr(user_data, 'cpf', ''),
            'is_active': getattr(user_data, 'is_active', True),
            'empresa_id': user_data.id,
            'tipo': user_type,
        }

        # Salva no Redis
        cache_key = f'token:{access_token}'
        await client.set(
            cache_key,
            json.dumps(session_data_for_cache, default=str),
            ex=86400,
        )

        LOGGER.info(f'Token salvo no cache. Chave: {mask_password(cache_key)}')

        # Retorna resposta padronizada
        return LoginResponse(
            id=user_data.id,
            username=getattr(user_data, 'username', ''),
            email=getattr(user_data, 'email', ''),
            empresa=getattr(user_data, 'company_name', ''),
            empresa_id=user_data.id,
            tipo=user_type,
            message='Login realizado com sucesso',
            access_token=access_token,
            refresh_token=refresh_token,
            token_type='bearer',
            session_id=str(uuid.uuid4()),
        )

    def _register_routes(self):
        @self.loginRT.post(
            '/login',
            response_model=LoginResponse,
            status_code=status.HTTP_200_OK,
        )
        async def login(user: OAuth2PasswordRequestForm = Depends()):
            LOGGER.info(f'🔐 Tentativa de login:  {mask_email(user.username)}')

            # 1. Primeiro tenta encontrar como ADMIN
            db_user = await Usuario.get_or_none(email=user.username)
            if db_user:
                return await self._authenticate_admin(
                    db_user, user.password, user.username
                )

            # 2. Se não encontrou admin, tenta como FUNCIONÁRIO
            db_employee = await Employees.get_or_none(email=user.username)
            if db_employee:
                return await self._authenticate_employee(
                    db_employee, user.password, user.username
                )

            # 3. Se não encontrou nenhum dos dois
            LOGGER.warning(
                f'Usuário não encontrado: {mask_email(user.username)}'
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Credenciais inválidas',
            )

        # --- Rota /logout ---
        @self.loginRT.post('/logout')
        async def logout(token: str = Depends(reuseable_oauth)):
            cache_key = f'token:{token}'
            exists = await client.exists(cache_key)
            if exists:
                await client.delete(cache_key)
                LOGGER.info(
                    f'Logout bem-sucedido. Chave removida: {mask_password(cache_key)}'
                )
                return {
                    'status': 200,
                    'message': 'Logout realizado com sucesso',
                }
            else:
                LOGGER.info(
                    f'Token não encontrado no cache: {mask_password(cache_key)}'
                )
                return {'status': 200, 'message': 'Sessão já encerrada'}

        # --- Rota /me ---
        @self.loginRT.get('/me')
        async def get_current_user_info(token: str = Depends(reuseable_oauth)):
            cache_key = f'token:{token}'
            user_data = await client.get(cache_key)

            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Token inválido ou expirado',
                )

            user_info = json.loads(user_data)
            return {
                'id': user_info.get('id'),
                'username': user_info.get('username'),
                'email': user_info.get('email'),
                'empresa': user_info.get('company_name'),
                'tipo': user_info.get('tipo'),
            }
