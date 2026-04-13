from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder

from src.auth.deps import SystemUser, get_current_user
from src.model.user import Usuario
from src.utils.get_produtos_user import get_product_by_user

buscar_produtos = APIRouter()


@buscar_produtos.get('/buscar', status_code=200)
async def get_product(
    code: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    current_user: SystemUser = Depends(get_current_user),
):
    """Busca produto por código ou nome e retorna JSON padronizado para frontend"""
    try:
        if not code and not name:
            return {
                'success': False,
                'data': None,
                'error': 'Informe código ou nome do produto',
            }

        product = await get_product_by_user(
            int(current_user.empresa_id), code, name
        )

        if not product:
            return {
                'success': False,
                'data': None,
                'error': 'Produto não encontrado',
            }

        return {
            'success': True,
            'data': jsonable_encoder(product),
            'error': None,
        }

    except Exception as e:
        return {
            'success': False,
            'data': None,
            'error': f'Erro inesperado: {str(e)}',
        }
