from fastapi import APIRouter

from .adjustments import router as update_item
from .create import router as create_router
from .delete import router as delete_router
from .list import router as list_router

cart_router = APIRouter(
    prefix='/carrinho',
    tags=['Carrinho'],
    responses={404: {'description': 'Não encontrado'}},
)

cart_router.include_router(create_router, prefix='')
cart_router.include_router(delete_router, prefix='')
cart_router.include_router(list_router, prefix='')
cart_router.include_router(update_item, prefix='')
