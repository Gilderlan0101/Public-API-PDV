import json
from datetime import datetime
from typing import List, Union

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from tortoise.exceptions import DoesNotExist

from src.auth.deps import SystemUser, get_current_user
from src.auth.deps_employes import SystemEmployees, get_current_employee
from src.core.cache import client
from src.model.employee import Employees
from src.model.product import Produto
from src.model.user import Usuario
from src.utils.user_or_functional import i_request

list_products = APIRouter()


@list_products.get('/list', status_code=200)
@i_request
async def list_all_products(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Lista todos os produtos do usuário ou do funcionário vinculado à empresa.
    O decorador @i_request já cuida do cache automaticamente.
    """
    try:
        if not current_user.empresa_id:
            return {
                'success': False,
                'data': None,
                'error': 'Usuário sem empresa vinculada.',
            }

        # Se chegou aqui, é porque o decorador não encontrou cache
        # e não encontrou produtos no banco, então executa a lógica original
        usuario_id = current_user.empresa_id

        # Busca produtos no banco
        products = await Produto.filter(usuario_id=usuario_id).all()
        products_data = jsonable_encoder(products)

        return {
            'success': True,
            'data': products_data,
            'error': None,
            'source': 'database',
        }  # Para debug

    except Exception as e:
        print(f'[ERROR] {str(e)}')
        return {
            'success': False,
            'data': None,
            'error': f'Erro inesperado: {str(e)}',
        }


@list_products.get('/funcionario/list', status_code=200)
@i_request
async def list_products_for_employee(
    current_employee: SystemEmployees = Depends(get_current_employee),
):
    """
    Lista todos os produtos da empresa do funcionário.
    O funcionário está autenticado e buscamos os produtos da empresa dele.
    """
    try:
        # O funcionário já está autenticado via get_current_employee
        # Precisamos buscar o usuario_id (empresa) do funcionário

        # Busca o funcionário com relacionamento para pegar o usuario_id
        employee = (
            await Employees.filter(id=current_employee.id)
            .select_related('usuario')
            .first()
        )

        if not employee:
            raise HTTPException(
                status_code=404, detail='Funcionário não encontrado'
            )

        if not employee:
            return {
                'success': False,
                'data': None,
                'error': 'Funcionário não vinculado a uma empresa.',
            }

        # O decorador @i_request vai automaticamente:
        # 1. Buscar no cache usando o usuario_id
        # 2. Se não tiver cache, buscar no banco
        # 3. Retornar os dados

        # Se chegou aqui, é porque o decorador não encontrou cache
        # e não encontrou produtos no banco, então executa a lógica original
        usuario_id = current_employee.empresa_id

        # Busca produtos no banco da empresa do funcionário
        products = await Produto.filter(usuario_id=usuario_id).all()
        products_data = jsonable_encoder(products)

        return {
            'success': True,
            'data': products_data,
            'error': None,
            'source': 'database',
            'empresa': employee.usuario.company_name if employee.id else 'N/A',
            'total_produtos': len(products_data),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f'[ERROR] Listagem para funcionário: {str(e)}')
        return {
            'success': False,
            'data': None,
            'error': f'Erro inesperado: {str(e)}',
        }
