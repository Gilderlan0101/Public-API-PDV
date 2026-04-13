import json
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from src.auth.auth_jwt import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from src.auth.deps_employes import (
    SystemEmployees,
    get_current_employee,
    reuseable_oauth,
)
from src.controllers.caixa.cash_controller import CashController
from src.core.cache import client
from src.logs.infos import LOGGER
from src.model.caixa import Caixa
from src.model.employee import Employees
from src.model.user import Usuario
from src.schemas.login.form_login_checkout import (
    CustomOAuth2PasswordRequestForm,
)
from src.utils.private_infos import mask_email, mask_password


# -------------------------------------------------------------
# SCHEMAS
# -------------------------------------------------------------
class TokenCaixaSchema(BaseModel):
    id: int
    username: str
    email: EmailStr
    empresa: Optional[str] = None
    empresa_id: Optional[int] = None
    tipo: str
    message: str
    access_token: str
    refresh_token: str
    token_type: str
    value: float
    caixa_id: int
    caixa_status: str


class ValidateTokenResponse(BaseModel):
    valid: bool
    user_id: int
    username: str
    empresa: str
    empresa_id: int
    caixa_aberto: bool
    caixa_id: Optional[int]
    saldo_inicial: Optional[float]
    message: str


# -------------------------------------------------------------
# CLASSE PRINCIPAL CORRIGIDA
# -------------------------------------------------------------
class LoginCheckout:
    """Contem as rotas de login/abertura de caixa e gerenciamento de sessao."""

    def __init__(self):
        self.router = APIRouter()
        self._register_routes()

    def _register_routes(self):

        # --- ROTA: /open (Login e Abertura de Caixa) ---
        @self.router.post(
            '/open',
            status_code=status.HTTP_200_OK,
            response_model=TokenCaixaSchema,
        )
        async def login_and_open(
            user: CustomOAuth2PasswordRequestForm = Depends(),
        ):
            """
            Login para funcionarios com verificacao de credenciais e abertura de caixa.
            """
            try:
                LOGGER.info(f'Tentativa de login: {mask_email(user.username)}')

                # Busca funcionario com relacionamento de usuario (empresa)
                employee = await Employees.get_or_none(
                    email=user.username
                ).select_related('usuario')

                # Diagnostico detalhado
                if not employee:
                    LOGGER.warning(
                        f'Email nao encontrado: {mask_email(user.username)}'
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail='Credenciais invalidas.',
                    )

                # Aplicando mascaras nas senhas para log
                LOGGER.info(
                    f'Diagnostico - Senha DB (employee): {mask_password(getattr(employee, "senha", "N/A")) if employee else "N/A"}'
                )

                LOGGER.info(
                    f'Diagnostico - Senha input: {mask_password(user.password)}'
                )

                user_id = None
                user_type = None
                employee_name = None
                company_id = None
                company_name = None
                user_email = None

                # Logica corrigida: Verifica primeiro se e funcionario
                if employee:
                    try:
                        # Valida senha do funcionario
                        if not verify_password(user.password, employee.senha):
                            # Tentativa alternativa de verificacao
                            if user.password == employee.senha:
                                LOGGER.warning(
                                    'Senha em texto puro detectada - considere hash BCrypt'
                                )
                                # Se funcionar com texto puro, continue (APENAS PARA DEV)
                                pass
                            else:
                                LOGGER.warning(
                                    f'Senha incorreta para funcionario: {mask_email(user.username)}'
                                )
                                raise HTTPException(
                                    status_code=status.HTTP_401_UNAUTHORIZED,
                                    detail='Credenciais invalidas.',
                                )

                        # Validacao de status do funcionario
                        if not employee.ativo:
                            LOGGER.warning(
                                f'Funcionario inativo: {mask_email(user.username)}'
                            )
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail='Funcionario inativo.',
                            )

                        if not employee.usuario:
                            LOGGER.warning(
                                f'Funcionario nao vinculado a empresa: {mask_email(user.username)}'
                            )
                            raise HTTPException(
                                status_code=status.HTTP_403_FORBIDDEN,
                                detail='Funcionario nao vinculado a uma empresa.',
                            )

                        # Dados basicos para uso posterior
                        company_id = employee.usuario_id
                        employee_name = employee.nome
                        company_name = employee.usuario.company_name
                        user_id = employee.id
                        user_type = 'funcionario'
                        user_email = employee.email

                        LOGGER.info(
                            f'Credenciais validas para FUNCIONARIO {employee_name} - Empresa: {company_name}'
                        )

                    except HTTPException:
                        raise
                    except Exception as e:
                        LOGGER.error(f'Erro na validacao do funcionario: {e}')
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail='Erro interno na validacao do funcionario',
                        )

                # Verificacao e abertura de caixa
                caixa_status = 'novo'
                try:
                    # Garantir que o valor_inicial seja float
                    try:
                        valor_inicial = float(user.valor_inicial)
                        if valor_inicial < 0:
                            raise ValueError(
                                'Valor inicial nao pode ser negativo'
                            )
                    except (ValueError, TypeError) as e:
                        LOGGER.error(
                            f'Valor inicial invalido: {user.valor_inicial} - Erro: {e}'
                        )
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Valor inicial deve ser um numero valido e positivo',
                        )

                    # CashController verifica se ja existe caixa aberto e retorna o objeto
                    caixa = await CashController.open_checkout(
                        employe_id=user_id,
                        initial_balance=valor_inicial,
                        name=employee_name,
                        company_id=company_id,
                    )

                    # Comparacao de datetimes com tratamento de timezone
                    if caixa.criado_em.tzinfo is not None:
                        agora = datetime.now(ZoneInfo('America/Sao_Paulo'))
                        criado_em_aware = caixa.criado_em
                    else:
                        agora = datetime.now()
                        criado_em_aware = caixa.criado_em.replace(tzinfo=None)

                    # Determina se o caixa foi aberto agora ou ja estava aberto
                    if criado_em_aware < (agora - timedelta(seconds=5)):
                        caixa_status = 'ja_aberto'
                        message = 'Login realizado - Caixa ja estava aberto.'
                        LOGGER.info(
                            f'Caixa ja estava aberto para {employee_name}: ID {caixa.caixa_id}'
                        )
                    else:
                        caixa_status = 'novo'
                        message = 'Login e Caixa abertos com sucesso.'
                        LOGGER.info(
                            f'Novo caixa aberto para {employee_name}: ID {caixa.caixa_id}'
                        )

                except HTTPException:
                    raise
                except Exception as e:
                    LOGGER.error(f'Erro ao abrir caixa para {user_id}: {e}')
                    import traceback

                    LOGGER.error(f'Stack trace: {traceback.format_exc()}')

                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f'Erro ao tentar abrir o caixa: {str(e)}',
                    )

                # Geracao de token e cache persistente
                access_token = create_access_token(str(user_id))
                refresh_token = create_refresh_token(str(user_id))

                LOGGER.info(
                    f'Tokens gerados para {employee_name} - Access Token: {mask_password(access_token)}'
                )

                # Cache: Armazenar os dados de autenticacao/sessao no Redis
                cache_key = f'token:{access_token}'

                # Dados a serem salvos
                session_cache_data = {
                    'id': user_id,
                    'email': user_email,
                    'empresa_id': company_id,
                    'caixa_id': caixa.caixa_id,
                    'username': employee_name,
                    'company_name': company_name,
                    'tipo': user_type,
                }

                # SET com expire time para seguranca (24 horas)
                try:
                    await client.setex(
                        cache_key,
                        86400,
                        json.dumps(session_cache_data, default=str),
                    )
                    LOGGER.debug(f'Cache salvo no Redis para {employee_name}')
                except Exception as e:
                    LOGGER.warning(
                        f'Falha ao salvar cache de token no Redis: {e}'
                    )
                    # Nao quebra o fluxo, apenas loga o warning

                # Retorno da resposta
                response_data = {
                    'id': user_id,
                    'username': employee_name,
                    'email': user_email,
                    'value': valor_inicial,
                    'empresa': company_name,
                    'empresa_id': company_id,
                    'tipo': user_type,
                    'message': message,
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'bearer',
                    'caixa_id': caixa.caixa_id,
                    'caixa_status': caixa_status,
                }

                LOGGER.info(
                    f'Login finalizado com sucesso para {employee_name} ({user_type}) - Caixa Status: {caixa_status}'
                )
                return response_data

            except HTTPException:
                raise
            except Exception as e:
                LOGGER.error(f'Erro inesperado em login_and_open: {e}')
                import traceback

                LOGGER.error(f'Stack trace: {traceback.format_exc()}')
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Erro interno no servidor',
                )

        # --- ROTA: /logout ---
        @self.router.post('/logout')
        async def logout(
            current_user: SystemEmployees = Depends(get_current_employee),
            token: str = Depends(reuseable_oauth),
        ):
            """
            Faz logout, invalida o token no cache (blocklist) e fecha o caixa.
            """
            LOGGER.info(f'Iniciando logout para User ID: {current_user.id}')

            # 1. Invalidacao do token no cache (Blocklist/Remocao)
            cache_key = f'token:{token}'
            removed = await client.delete(cache_key)

            if removed == 0:
                LOGGER.debug(
                    'Token nao encontrado em cache (ja expirou ou foi removido).'
                )
            else:
                LOGGER.debug('Token removido do cache com sucesso.')

            # 2. Fechamento do caixa
            try:
                close_checkout = await Caixa.filter(
                    funcionario_id=current_user.id,
                    usuario_id=current_user.empresa_id,
                    aberto=True,
                ).update(
                    aberto=False,
                    atualizado_em=datetime.now(ZoneInfo('America/Sao_Paulo')),
                )

                if close_checkout > 0:
                    LOGGER.info(
                        f'Caixa fechado com sucesso para User ID: {current_user.id}'
                    )
                    return {
                        'status': status.HTTP_200_OK,
                        'message': 'Logout e caixa fechados com sucesso.',
                    }

                # Se o caixa ja estava fechado:
                LOGGER.warning(
                    f'Logout OK, mas caixa ja estava fechado para User ID: {current_user.id}'
                )
                return {
                    'status': status.HTTP_200_OK,
                    'message': 'Logout realizado. O caixa ja estava fechado.',
                }

            except Exception as e:
                LOGGER.error(
                    f'Erro critico ao fechar o caixa (User ID: {current_user.id}): {e}'
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Erro interno ao finalizar o caixa.',
                )

        # --- ROTA: /validate (Otimizada) ---
        @self.router.get('/validate', response_model=ValidateTokenResponse)
        async def validate_token(
            current_user: SystemEmployees = Depends(get_current_employee),
        ):
            """
            Valida se o token JWT e valido e se o caixa esta aberto, usando o cache.
            """
            LOGGER.debug(f'Validando token para User ID: {current_user.id}')

            # 1. Verifica se o caixa esta aberto (ultimo caixa aberto)
            caixa_aberto = (
                await Caixa.filter(
                    funcionario_id=current_user.id,
                    usuario_id=current_user.empresa_id,
                    aberto=True,
                )
                .order_by('-id')
                .first()
            )

            # 2. Construcao da resposta de validacao
            if caixa_aberto:
                message = 'Token e sessao validos - Caixa aberto.'
                LOGGER.debug(
                    f'Validacao positiva para User ID: {current_user.id} - Caixa ID: {caixa_aberto.caixa_id}'
                )
            else:
                message = 'Token valido, mas caixa nao esta aberto.'
                LOGGER.warning(
                    f'Token valido mas caixa fechado para User ID: {current_user.id}'
                )

            return ValidateTokenResponse(
                valid=True,
                user_id=current_user.id,
                username=current_user.username,
                empresa=current_user.company_name,
                empresa_id=current_user.empresa_id,
                caixa_aberto=bool(caixa_aberto),
                caixa_id=caixa_aberto.caixa_id if caixa_aberto else None,
                saldo_inicial=float(caixa_aberto.saldo_inicial)
                if caixa_aberto
                else None,
                message=message,
            )

        # --- ROTA: /caixa/status (Simplificada) ---
        @self.router.get('/caixa/status')
        async def get_caixa_status(
            current_user: SystemEmployees = Depends(get_current_employee),
        ):
            """
            Retorna o status atual do caixa do funcionario.
            """
            LOGGER.debug(
                f'Consultando status do caixa para User ID: {current_user.id}'
            )

            try:
                caixa_aberto = await Caixa.filter(
                    funcionario_id=current_user.id,
                    usuario_id=current_user.empresa_id,
                    aberto=True,
                ).first()

                if caixa_aberto:
                    response_data = {
                        'caixa_aberto': True,
                        'caixa_id': caixa_aberto.caixa_id,
                        'saldo_inicial': caixa_aberto.saldo_inicial,
                        'saldo_atual': caixa_aberto.saldo_atual,
                        'aberto_em': caixa_aberto.criado_em,
                        'message': 'Caixa esta aberto',
                    }
                    LOGGER.debug(
                        f'Caixa encontrado: ID {caixa_aberto.caixa_id} para User ID: {current_user.id}'
                    )
                    return response_data
                else:
                    LOGGER.debug(
                        f'Nenhum caixa aberto encontrado para User ID: {current_user.id}'
                    )
                    return {
                        'caixa_aberto': False,
                        'message': 'Nenhum caixa aberto encontrado',
                    }

            except Exception as e:
                LOGGER.error(
                    f'Erro ao verificar status do caixa para User ID: {current_user.id}: {e}'
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail='Erro ao verificar status do caixa',
                )
