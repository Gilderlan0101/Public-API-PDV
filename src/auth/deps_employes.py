import logging
import os
from datetime import datetime
from typing import Final

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, ValidationError

from src.auth.auth_jwt import (
    ALGORITHM,
    JWT_SECRET_KEY,
    verify_password,
)
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
    checkout_id: int
    tipo: str  # 'admin' ou 'funcionario'

    model_config = {'from_attributes': True}


# -------------------------------------------------------------
# 2. Configuração do OAuth2
# -------------------------------------------------------------

reuseable_oauth: Final = OAuth2PasswordBearer(
    tokenUrl='/api/v1/caixa/checkout/open', scheme_name='JWT', auto_error=False
)

# -------------------------------------------------------------
# 3. Funções de Autenticação (ADMIN E FUNCIONÁRIO)
# -------------------------------------------------------------


async def authenticate_user(email: str, password: str):
    """
    Autentica um usuário (admin ou funcionário) por email e senha.

    Args:
        email: Email do usuário
        password: Senha em texto puro

    Returns:
        Tuple: (user_object, user_type) onde user_type é 'admin' ou 'funcionario'

    Raises:
        HTTPException: 401 para credenciais inválidas
    """
    LOGGER.info(f'Tentativa de autenticacao para: {email}')

    # Primeiro tenta encontrar como funcionário
    employee = await Employees.get_or_none(email=email).select_related(
        'usuario'
    )

    if employee:
        # Verifica senha do funcionário
        if not verify_password(password, employee.senha):
            LOGGER.warning(f'Senha incorreta para funcionario: {email}')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Credenciais invalidas',
            )

        # Verifica se funcionário está ativo
        if not employee.ativo:
            LOGGER.warning(f'Funcionario inativo: {email}')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Funcionario inativo',
            )

        # Verifica se tem empresa vinculada
        if not employee.usuario:
            LOGGER.warning(f'Funcionario sem empresa: {email}')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Funcionario nao vinculado a uma empresa',
            )

        LOGGER.info(f'Autenticacao bem-sucedida para funcionario: {email}')
        return employee, 'funcionario'

    # Se não encontrou funcionário, tenta como admin
    admin = await Usuario.get_or_none(email=email)

    if admin:
        # Verifica senha do admin
        if not verify_password(password, admin.password):
            LOGGER.warning(f'Senha incorreta para admin: {email}')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Credenciais invalidas',
            )

        # Verifica se admin está ativo
        if not admin.is_active:
            LOGGER.warning(f'Admin inativo: {email}')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Administrador inativo',
            )

        LOGGER.info(f'Autenticacao bem-sucedida para admin: {email}')
        return admin, 'admin'

    # Se não encontrou nenhum dos dois
    LOGGER.warning(f'Email nao encontrado: {email}')
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Credenciais invalidas',
    )


# -------------------------------------------------------------
# 4. Função de Dependência Principal (CORRIGIDA PARA ADMIN E FUNCIONÁRIO)
# -------------------------------------------------------------


async def get_current_employee(
    token: str = Depends(reuseable_oauth),
) -> SystemEmployees:
    """
    Decodifica o token JWT e retorna os dados do usuário (admin ou funcionário).
    """

    # Validação do Token JWT
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        token_data = TokenPayload(**payload)

        # Verifica expiração
        if (
            token_data.exp is None
            or datetime.fromtimestamp(token_data.exp) < datetime.now()
        ):
            LOGGER.info('Token expirado na validacao de dependencia.')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token expirado. Faca login novamente.',
                headers={'WWW-Authenticate': 'Bearer'},
            )

    except (JWTError, ValidationError) as erro:
        LOGGER.error(f'Falha na decodificacao/validacao do token: {erro}')
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Nao foi possível validar suas credenciais.',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    user_id = int(token_data.sub)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Token invalido: identificador (sub) ausente.',
        )

    # Busca do Usuário (Funcionário ou Admin)
    user_object = None
    user_type = None
    username = None
    company_name = None
    email = None
    empresa_id = None

    # Primeiro tenta buscar como funcionário
    employee = await Employees.get_or_none(id=user_id).select_related(
        'usuario'
    )

    if employee:
        if not employee.ativo:
            LOGGER.warning(
                f'Funcionario {employee.id} tentou acessar mas esta inativo.'
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Funcionario inativo.',
            )

        if not employee.usuario:
            LOGGER.warning(f'Funcionario {employee.id} sem empresa vinculada.')
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Funcionario nao vinculado a uma empresa.',
            )

        admin = employee.usuario
        user_object = employee
        user_type = 'funcionario'
        username = employee.nome
        company_name = admin.company_name
        email = employee.email
        empresa_id = admin.id

        LOGGER.info(
            f'Funcionario {employee.id} da EMPRESA {admin.company_name} validado via JWT.'
        )

    # Se não encontrou funcionário, tenta como admin
    else:
        admin = await Usuario.get_or_none(id=user_id)

        if admin:
            if not admin.is_active:
                LOGGER.warning(
                    f'Admin {admin.id} tentou acessar mas esta inativo.'
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail='Administrador inativo.',
                )

            user_object = admin
            user_type = 'admin'
            username = admin.username
            company_name = admin.company_name
            email = admin.email
            empresa_id = admin.id

            LOGGER.info(
                f'Admin {admin.id} da EMPRESA {admin.company_name} validado via JWT.'
            )

    # Se não encontrou nenhum dos dois
    if not user_object:
        LOGGER.warning(
            f'Tentativa de acesso com ID {user_id} falhou: Usuario nao encontrado.'
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Usuario nao encontrado.',
        )

    # Busca do CAIXA ABERTO (APENAS VERIFICAÇÃO)
    checkout_id = None

    if user_type == 'funcionario':
        caixa_aberto = (
            await Caixa.filter(
                funcionario_id=user_object.id,
                usuario_id=empresa_id,
                aberto=True,
            )
            .order_by('-id')
            .first()
        )
        checkout_id = caixa_aberto.id if caixa_aberto else None
    else:  # admin
        caixa_aberto = (
            await Caixa.filter(
                funcionario_id=user_object.id,  # Admin usa próprio ID como funcionario_id
                usuario_id=empresa_id,
                aberto=True,
            )
            .order_by('-id')
            .first()
        )
        checkout_id = caixa_aberto.id if caixa_aberto else None

    if not checkout_id:
        LOGGER.warning(
            f'Usuario {user_object.id} autenticado mas sem caixa aberto'
        )

    # Retorno dos Dados
    return SystemEmployees(
        id=user_object.id,
        username=username,
        company_name=company_name,
        email=email,
        empresa_id=empresa_id,
        checkout_id=checkout_id,
        tipo=user_type,
    )


# Função auxiliar para verificar se é admin
async def get_current_admin(
    current_user: SystemEmployees = Depends(get_current_employee),
) -> SystemEmployees:
    """
    Dependência que garante que o usuário atual é um administrador.
    """
    if current_user.tipo != 'admin':
        LOGGER.warning(
            f'Usuario {current_user.id} tentou acessar recurso de admin sem permissao'
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Acesso restrito a administradores',
        )
    return current_user


# Função auxiliar para verificar se é funcionário
async def get_current_funcionario(
    current_user: SystemEmployees = Depends(get_current_employee),
) -> SystemEmployees:
    """
    Dependência que garante que o usuário atual é um funcionário.
    """
    if current_user.tipo != 'funcionario':
        LOGGER.warning(
            f'Admin {current_user.id} tentou acessar recurso de funcionario'
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Acesso restrito a funcionarios',
        )
    return current_user
