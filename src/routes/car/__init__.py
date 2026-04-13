from fastapi import APIRouter

# Importacao das rotas especificas do modulo de carrinho
from .adjustments import router as update_router
from .create import router as create_router
from .delete import router as delete_router
from .list import router as list_router

"""
Este router agrupa as sub-operacoes do carrinho de compras.
O prefixo base '/api/v1/cart' e a tag 'Cart and Sales' sao definidos
no RouterManager central para garantir a padronizacao.
"""

cart_router = APIRouter(
    responses={404: {'description': 'Cart resource not found'}},
)

# Inclusao das rotas filhas sem duplicacao de prefixos
cart_router.include_router(create_router)
cart_router.include_router(delete_router)
cart_router.include_router(list_router)
cart_router.include_router(update_router)
