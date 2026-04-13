import logging
import os
from datetime import datetime
from typing import Any, Final, Optional, Tuple
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, EmailStr, ValidationError

from src.auth.auth_jwt import ALGORITHM, JWT_SECRET_KEY, verify_password
from src.logs.infos import LOGGER
from src.model.caixa import Caixa
from src.model.employee import Employees
from src.model.user import Usuario
from src.schemas.schema_user import TokenPayload

# -------------------------------------------------------------
# 1. Schemas de Retorno
# -------------------------------------------------------------


class SystemEmployees(BaseModel):
    id: int
    username: str
    company_name: str
    email: EmailStr
    empresa_id: int
    checkout_id: Optional[
        int
    ] = None  # FIX: Pode ser None se o caixa estiver fechado
    tipo: str  # 'admin' ou 'funcionario'

    model_config = ConfigDict(from_attributes=True)


# -------------------------------------------------------------
# 2. Configuração do OAuth2
# -------------------------------------------------------------

reuseable_oauth: Final = OAuth2PasswordBearer(
    tokenUrl='/api/v1/caixa/checkout/open', scheme_name='JWT', auto_error=False
)

# -------------------------------------------------------------
# 3. Funções Auxiliares de Busca e Validação
# -------------------------------------------------------------


async def _get_active_checkout(user_id: int, empresa_id: int) -> Optional[int]:
    """Busca o ID do caixa aberto para qualquer tipo de operador."""
    caixa = (
        await Caixa.filter(
            funcionario_id=user_id, usuario_id=empresa_id, aberto=True
        )
        .order_by('-id')
        .first()
    )
    return caixa.id if caixa else None


def _validate_token(token: str) -> int:
    """Decodifica o JWT e valida a expiração."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)

        if not token_data.sub:
            raise ValueError('Identificador (sub) ausente')

        if (
            token_data.exp
            and datetime.fromtimestamp(token_data.exp) < datetime.now()
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token expirado. Faca login novamente.',
                headers={'WWW-Authenticate': 'Bearer'},
            )
        return int(token_data.sub)
    except (JWTError, ValidationError, ValueError) as e:
        LOGGER.error(f'Erro na validacao do token: {e}')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Nao foi possivel validar suas credenciais.',
            headers={'WWW-Authenticate': 'Bearer'},
        )


# -------------------------------------------------------------
# 4. Funções de Autenticação (ADMIN E FUNCIONÁRIO)
# -------------------------------------------------------------


async def authenticate_user(email: str, password: str) -> Tuple[Any, str]:
    """Autentica um usuario (admin ou funcionario) por email e senha."""
    LOGGER.info(f'Tentativa de autenticacao: {email}')

    # 1. Tentativa como Funcionario
    user = await Employees.get_or_none(email=email).select_related('usuario')
    u_type = 'funcionario'

    # 2. Se nao for funcionario, tenta como Admin
    if not user:
        user = await Usuario.get_or_none(email=email)
        u_type = 'admin'

    if not user:
        LOGGER.warning(f'Usuario nao encontrado: {email}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Credenciais invalidas',
        )

    # 3. Validacoes Genericas (Ativo e Senha)
    is_active = user.ativo if u_type == 'funcionario' else user.is_active
    pwd_hash = user.senha if u_type == 'funcionario' else user.password

    if not is_active:
        LOGGER.warning(f'Usuario inativo: {email}')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail='Usuario inativo'
        )

    if not verify_password(password, pwd_hash):
        LOGGER.warning(f'Senha incorreta: {email}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Credenciais invalidas',
        )

    # 4. Validacao especifica de vinculo para funcionarios
    if u_type == 'funcionario' and not user.usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Funcionario sem empresa vinculada',
        )

    return user, u_type


# -------------------------------------------------------------
# 5. Função de Dependência Principal
# -------------------------------------------------------------


async def get_current_employee(
    token: str = Depends(reuseable_oauth),
) -> SystemEmployees:
    """Recupera os dados do usuario logado atraves do token JWT."""
    user_id = _validate_token(token)

    # Busca Sequencial Otimizada
    # Tentativa 1: Funcionario
    employee = await Employees.get_or_none(id=user_id).select_related(
        'usuario'
    )

    if employee:
        if not employee.ativo or not employee.usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Acesso negado: Funcionario inativo ou sem empresa',
            )

        target_id = employee.usuario.id
        data = {
            'id': employee.id,
            'username': employee.nome,
            'company_name': employee.usuario.company_name,
            'email': employee.email,
            'empresa_id': target_id,
            'tipo': 'funcionario',
        }
    else:
        # Tentativa 2: Admin
        admin = await Usuario.get_or_none(id=user_id)
        if not admin or not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Usuario inexistente ou inativo',
            )

        target_id = admin.id
        data = {
            'id': admin.id,
            'username': admin.username,
            'company_name': admin.company_name,
            'email': admin.email,
            'empresa_id': target_id,
            'tipo': 'admin',
        }

    # Busca de Caixa Aberto (Comum a ambos)
    checkout_id = await _get_active_checkout(data['id'], data['empresa_id'])

    if not checkout_id:
        LOGGER.warning(
            f"Operador {data['id']} ({data['tipo']}) acessando sem caixa aberto"
        )

    return SystemEmployees(**data, checkout_id=checkout_id)


# -------------------------------------------------------------
# 6. Funções de Autorização
# -------------------------------------------------------------


async def get_current_admin(
    current_user: SystemEmployees = Depends(get_current_employee),
) -> SystemEmployees:
    """Garante que o usuario e um administrador."""
    if current_user.tipo != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Acesso restrito a administradores',
        )
    return current_user


async def get_current_funcionario(
    current_user: SystemEmployees = Depends(get_current_employee),
) -> SystemEmployees:
    """Garante que o usuario e um funcionario."""
    if current_user.tipo != 'funcionario':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Acesso restrito a funcionarios',
        )
    return current_user
