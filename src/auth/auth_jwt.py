# auth_jwt.py

import logging
import os
from datetime import datetime, timedelta
from typing import Any, Optional, Union
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

load_dotenv()

# Configuração de logging
logger = logging.getLogger(__name__)

# Chamando as variaves de ambiete que vmos usar neste arquivo
ALGORITHM = os.getenv('ALGORITHM', 'HS256')
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')
JWT_REFRESH_SECRET_KEY = os.getenv(
    'JWT_REFRESH_SECRET_KEY', 'default_jwt_refresh_secret_key'
)

ACCESS_TOKEN_EXPIRE_MINUTES = 28800  # 8 horas
REFRESH_TOKEN_EXPIRE_MINUTES = 60 * 24 * 1  # 1 day

password_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def get_hashed_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, hashed_pass: str) -> bool:
    return password_context.verify(password, hashed_pass)


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[int] = None
) -> str:
    expire = (
        datetime.now(ZoneInfo('America/Sao_Paulo'))
        + timedelta(minutes=expires_delta)
        if expires_delta
        else datetime.now(ZoneInfo('America/Sao_Paulo'))
        + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode = {'exp': expire, 'sub': str(subject)}
    return jwt.encode(to_encode, JWT_SECRET_KEY, ALGORITHM)  # type: ignore


def create_refresh_token(
    subject: Union[str, Any], expires_delta: Optional[int] = None
) -> str:
    expire = (
        datetime.now(ZoneInfo('America/Sao_Paulo'))
        + timedelta(minutes=expires_delta)
        if expires_delta
        else datetime.now(ZoneInfo('America/Sao_Paulo'))
        + timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)
    )

    to_encode = {'exp': expire, 'sub': str(subject)}
    # type: ignore
    return jwt.encode(to_encode, JWT_REFRESH_SECRET_KEY, ALGORITHM)


# 🔥 NOVA FUNÇÃO: Verificar token JWT
def verify_token(token: str) -> str:
    """
    Verifica se um token JWT é válido e retorna o employee_id (subject)

    Args:
        token (str): Token JWT a ser validado

    Returns:
        str: Employee ID (subject) do token

    Raises:
        HTTPException: Se o token for inválido ou expirado
    """
    try:
        logger.info('🔐 Validando token JWT...')

        # Decodifica o token
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])

        # Obtém o subject (employee_id)
        employee_id: str = payload.get('sub')

        if employee_id is None:
            logger.warning('❌ Token sem subject (sub)')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Token inválido: subject não encontrado',
            )

        # Verifica se o token expirou (jwt.decode já faz isso automaticamente)
        # Mas podemos fazer uma verificação adicional se necessário
        exp_timestamp = payload.get('exp')
        if exp_timestamp:
            exp_datetime = datetime.fromtimestamp(
                exp_timestamp, tz=ZoneInfo('America/Sao_Paulo')
            )
            if exp_datetime < datetime.now(ZoneInfo('America/Sao_Paulo')):
                logger.warning(
                    f'❌ Token expirado para employee_id: {employee_id}'
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail='Token expirado',
                )

        logger.info(f'✅ Token válido para employee_id: {employee_id}')
        return employee_id

    except JWTError as e:
        logger.error(f'❌ Erro JWT na verificação do token: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Token inválido: {str(e)}',
        )
    except Exception as e:
        logger.error(f'❌ Erro inesperado na verificação do token: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno na validação do token',
        )


# 🔥 FUNÇÃO ADICIONAL: Verificar refresh token
def verify_refresh_token(token: str) -> str:
    """
    Verifica se um refresh token JWT é válido

    Args:
        token (str): Refresh token JWT a ser validado

    Returns:
        str: Employee ID (subject) do token
    """
    try:
        logger.info('🔐 Validando refresh token JWT...')

        payload = jwt.decode(
            token, JWT_REFRESH_SECRET_KEY, algorithms=[ALGORITHM]
        )

        employee_id: str = payload.get('sub')

        if employee_id is None:
            logger.warning('❌ Refresh token sem subject (sub)')
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Refresh token inválido',
            )

        logger.info(f'✅ Refresh token válido para employee_id: {employee_id}')
        return employee_id

    except JWTError as e:
        logger.error(f'❌ Erro JWT na verificação do refresh token: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Refresh token expirado ou inválido',
        )


# 🔥 FUNÇÃO ADICIONAL: Obter dados do payload sem verificar expiração
def get_token_payload(token: str) -> dict:
    """
    Obtém o payload do token sem verificar a expiração
    Útil para debugging ou logs
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={'verify_exp': False},
        )  # Não verifica expiração
        return payload
    except JWTError as e:
        logger.error(f'Erro ao decodificar payload do token: {str(e)}')
        return {}


# 🔥 FUNÇÃO ADICIONAL: Verificar se o token está prestes a expirar
def is_token_expiring_soon(token: str, minutes_before: int = 30) -> bool:
    """
    Verifica se o token irá expirar em breve

    Args:
        token (str): Token JWT
        minutes_before (int): Minutos antes da expiração para considerar "em breve"

    Returns:
        bool: True se o token expira em breve
    """
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[ALGORITHM],
            options={'verify_exp': False},
        )

        exp_timestamp = payload.get('exp')
        if not exp_timestamp:
            return False

        exp_datetime = datetime.fromtimestamp(
            exp_timestamp, tz=ZoneInfo('America/Sao_Paulo')
        )
        now = datetime.now(ZoneInfo('America/Sao_Paulo'))

        time_until_expiry = exp_datetime - now
        minutes_until_expiry = time_until_expiry.total_seconds() / 60

        return minutes_until_expiry <= minutes_before

    except JWTError:
        return False
