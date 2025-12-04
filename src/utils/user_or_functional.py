import inspect
import json
from functools import wraps

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder

from src.core.cache import client
from src.logs.infos import LOGGER
from src.model.employee import Employees
from src.model.product import Produto
from src.model.user import Usuario

"""
user_or_functional: Este arquivo é responsável por identificar quem está tentando acessar o sistema.

Ele busca dados de acordo com as permissões do usuário. 
Usuários com permissão de administrador têm acesso à quase toda a funcionalidade do sistema, 
exceto ao PDV (Ponto de Venda) ou abertura de caixa. Funcionários, 
por outro lado, têm acesso apenas ao PDV ou à função de abrir caixa.  
A função implementada é um decorador, utilizado em rotas e funções internas.
"""


def i_request(function):
    """
    Decorador principal para controle de acesso e cache baseado no tipo de usuário.

    Funcionalidades:
    - Cache automático de produtos para usuários do tipo empresa
    - Controle de acesso baseado no tipo de usuário (SystemUser vs SystemEmployees)
    - Redirecionamento para lógicas específicas conforme o parâmetro identificado
    """

    # Preserva os metadados da função original como nome, docstring e assinatura
    @wraps(function)
    async def wrapper(*args, **kwargs):
        """
        Wrapper que intercepta a chamada da função e aplica a lógica de controle de acesso
        """

        # Executa a função original se nenhuma lógica específica foi aplicada
        return await function(*args, **kwargs)

    return wrapper


async def handle_current_user_logic(function, params, args, kwargs):
    """
    Lógica específica para tratamento de usuários autenticados (current_user)

    Responsabilidades:
    - Identificar o tipo de usuário (SystemUser ou SystemEmployees)
    - Aplicar regras de acesso baseadas no tipo de usuário e função alvo
    - Bloquear acessos não autorizados com HTTP 403
    """

    try:
        # Obtém o índice do parâmetro current_user nos argumentos
        index = params.index('current_user')

        # Recupera o objeto current_user dos argumentos posicionais ou nomeados
        current_user = (
            args[index] if index < len(args) else kwargs.get('current_user')
        )

        # Retorna early se não houver usuário autenticado
        if not current_user:
            return

        # Identifica o tipo do usuário e o nome da função sendo acessada
        user_type = type(current_user).__name__
        function_name = function.__name__

        # Registra informações de debug no log
        LOGGER.info(f'User type: {user_type}, Function: {function_name}')

        # Define as rotas que são exclusivas para funcionários
        EMPLOYEE_ONLY_ROUTES = {
            'get_delivery_management',
            'update_delivery_status',
            'manage_orders',
            'get_caixa_status' 'list_all_products',
        }

        # Define as rotas que são exclusivas para empresas (SystemUser)
        USER_ONLY_ROUTES = {'list_all_products'}

        # Bloqueia SystemUser tentando acessar rotas exclusivas de funcionários
        if user_type == 'SystemUser' and function_name in EMPLOYEE_ONLY_ROUTES:
            LOGGER.warning(f'SystemUser bloqueado na rota: {function_name}')
            raise HTTPException(
                status_code=403, detail='Acesso restrito para funcionários'
            )

        # Bloqueia SystemEmployees tentando acessar rotas exclusivas de empresas
        elif (
            user_type == 'SystemEmployees'
            and function_name in USER_ONLY_ROUTES
        ):
            LOGGER.warning(
                f'SystemEmployees bloqueado na rota: {function_name}'
            )
            raise HTTPException(
                status_code=403, detail='Acesso restrito para empresas'
            )

        # Executa lógica específica baseada no tipo de usuário
        if user_type == 'SystemUser':
            await handle_system_user_logic(current_user, function_name)

        elif user_type == 'SystemEmployees':
            await handle_system_employee_logic(current_user, function_name)

    # Propaga exceções HTTP (como acesso negado) para o cliente
    except HTTPException:
        raise

    except Exception as e:
        # Registra erros inesperados durante o processamento
        LOGGER.error(f'Erro em handle_current_user_logic: {e}')
