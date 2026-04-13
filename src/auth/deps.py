# deps.py - Versão Final com Cache

import json
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, ValidationError
from redis.asyncio import Redis  # Adicionado para tipagem

from src.auth.auth_jwt import ALGORITHM, JWT_SECRET_KEY

# Assumindo que você tem um cliente Redis Async global (client)
from src.core.cache import client
from src.model.employee import Employees
from src.model.membros import (
    Membro,
)  # Manter Employees e Membro para o lookup de usuario
from src.model.user import Usuario
from src.schemas.schema_user import (
    TokenPayload,
)  # Assumindo que TokenPayload existe

reuseable_oauth = OAuth2PasswordBearer(
    tokenUrl='/api/v1/auth/login', scheme_name='JWT'
)


class SystemUser(BaseModel):
    id: int
    username: str
    email: EmailStr
    company_name: Optional[str] = None
    cnpj: Optional[str] = None
    cpf: Optional[str] = None
    gerente: Optional[str] = None
    is_active: bool = True
    empresa_id: Optional[int] = None

    model_config = {'from_attributes': True}


async def get_current_user(
    token: str = Depends(reuseable_oauth),
) -> SystemUser:

    # 🎯 PASSO 1: Tenta buscar os dados do usuario no CACHE (Fast Path)
    cache_key = f'token:{token}'
    user_data_json = await client.get(cache_key)

    if user_data_json:
        # Se encontrado, desserializa e retorna SystemUser rapidamente
        user_data = json.loads(user_data_json)
        # O cache armazena SystemUser, exceto o 'token'
        return SystemUser(**user_data)

    # 🎯 PASSO 2: Validacao JWT (Slow Path, se nao estiver em cache)
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)

        # Verificacao de expiracao (ja feito pela decodificacao, mas mantido para clareza)
        if (
            token_data.exp is None
            or datetime.fromtimestamp(token_data.exp) < datetime.now()
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token expirado. Faça login novamente.',
                headers={'WWW-Authenticate': 'Bearer'},
            )

    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Não foi possível validar suas credenciais.',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    user_id = int(token_data.sub)

    # 🎯 PASSO 3: Busca no DB e Reconstrucao do Cache

    # Tenta buscar como Usuario (dono)
    user_db = await Usuario.get_or_none(id=user_id)
    if user_db:
        # Mapeia para o modelo SystemUser (incluindo empresa_id)
        system_user_data = SystemUser(
            id=user_db.id,
            username=user_db.username,
            email=user_db.email,
            company_name=user_db.company_name,
            cnpj=user_db.cnpj,
            cpf=user_db.cpf,
            is_active=user_db.is_active,
            empresa_id=user_db.id,
        ).model_dump()

        # Salva no cache antes de retornar
        await client.set(cache_key, json.dumps(system_user_data, default=str))
        return SystemUser(**system_user_data)

    # Tenta com funcionario
    employee_db = await Employees.get_or_none(id=user_id).select_related(
        'usuario'
    )
    if employee_id:
        target = employee_db.usuario

        # Mapeia para modelo SystemUser
        system_user_data = SystemUser(
            id=employee_db.id,
            username=employee_db.nome,
            email=employee_db.email,
            company_name=target.company_name,
            cnpj=None,
            cpf=None,
            gerente=None,
            ativo=employee_db.ativo,
            empresa_id=target.id,
        ).model_dump()

        # salva no cache de retorna
        await client.set(cache_key, json.dumps(system_user_data, default=str))
        return SystemUser(**system_user_data)

    # Tenta buscar como Membro (logica de Membro omitida para brevidade, mas deve seguir aqui)
    membro_db = await Membro.get_or_none(id=user_id).select_related('usuario')
    if membro_db:
        usuario_dono = membro_db.usuario

        # Mapeia para o modelo SystemUser
        system_user_data = SystemUser(
            id=membro_db.id,
            username=membro_db.nome,
            email=membro_db.email or usuario_dono.email,
            company_name=usuario_dono.company_name,
            cnpj=usuario_dono.cnpj,
            cpf=membro_db.cpf,
            gerente=membro_db.gerente,
            is_active=membro_db.ativo,
            empresa_id=usuario_dono.id,
        ).model_dump()

        # Salva no cache antes de retornar
        await client.set(cache_key, json.dumps(system_user_data, default=str))
        return SystemUser(**system_user_data)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='Usuário não encontrado após validação do token.',
    )
