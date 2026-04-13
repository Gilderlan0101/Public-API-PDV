import json
from datetime import datetime
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, EmailStr, ValidationError

from src.auth.auth_jwt import ALGORITHM, JWT_SECRET_KEY
from src.core.cache import client
from src.model.membros import Membro
from src.model.user import Usuario
from src.schemas.schema_user import TokenPayload

# Configurações de tempo de Cache (em segundos)
CACHE_TTL = 3600  # 1 hora

reuseable_oauth = OAuth2PasswordBearer(
    tokenUrl='/api/v1/auth/login', scheme_name='JWT'
)

# -------------------------------------------------------------
# 1. Schemas de Retorno (Definido primeiro para evitar NameError)
# -------------------------------------------------------------


class SystemUser(BaseModel):
    """Representa o Usuário (Dono/Empresa) ou Membro."""

    id: int
    username: str
    email: EmailStr
    company_name: Optional[str] = None
    cnpj: Optional[str] = None
    cpf: Optional[str] = None
    gerente: Optional[str] = None
    is_active: bool = True
    empresa_id: Optional[int] = None  # ID do dono da empresa (Usuario.id)

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# 2. Funções Auxiliares
# -------------------------------------------------------------


async def set_user_cache(token: str, data: dict):
    """Helper para salvar dados serializados no cache Redis."""
    cache_key = f'token:{token}'
    await client.set(cache_key, json.dumps(data, default=str), ex=CACHE_TTL)


# -------------------------------------------------------------
# 3. Dependência de Autenticação Principal
# -------------------------------------------------------------


async def get_current_user(
    token: str = Depends(reuseable_oauth),
) -> SystemUser:
    """
    Dependência que recupera o usuário (Dono ou Membro) validando o token e o cache.
    """
    cache_key = f'token:{token}'
    cached_data = await client.get(cache_key)

    if cached_data:
        # Se encontrado no cache, retorna o objeto SystemUser imediatamente
        return SystemUser(**json.loads(cached_data))

    # Validação do JWT (Caminho mais lento, ocorre apenas se não houver cache)
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)

        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token expirado. Realize o login novamente.',
                headers={'WWW-Authenticate': 'Bearer'},
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Credenciais inválidas ou token malformado.',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    user_id = int(token_data.sub)

    # Busca Sequencial no Banco de Dados

    # 1. Tenta buscar como Dono da Empresa (Usuario)
    owner = await Usuario.get_or_none(id=user_id)
    if owner:
        user_map = SystemUser(
            id=owner.id,
            username=owner.username,
            email=owner.email,
            company_name=owner.company_name,
            cnpj=owner.cnpj,
            cpf=owner.cpf,
            is_active=owner.is_active,
            empresa_id=owner.id,
        ).model_dump()

        await set_user_cache(token, user_map)
        return SystemUser(**user_map)

    # 2. Tenta buscar como Membro de equipe
    member = await Membro.get_or_none(id=user_id).select_related('usuario')
    if member:
        biz = member.usuario   # biz representa a empresa vinculada
        user_map = SystemUser(
            id=member.id,
            username=member.nome,
            email=member.email or biz.email,
            company_name=biz.company_name,
            cnpj=biz.cnpj,
            cpf=member.cpf,
            gerente=member.gerente,
            is_active=member.ativo,
            empresa_id=biz.id,
        ).model_dump()

        await set_user_cache(token, user_map)
        return SystemUser(**user_map)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail='Usuário autenticado não localizado na base de dados.',
    )
