import re

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.deps import get_current_user
from src.controllers.products.products_infors import Products
from src.schemas.schema_user import SystemUser

product_deep_infos = APIRouter(prefix='/produtos', tags=['Produtos'])


@product_deep_infos.get('/buscar-dados')
async def search_products(
    current_user: SystemUser = Depends(get_current_user),
    product_name: str = Query(..., description='Nome do produto'),
):
    if not current_user.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Usuário sem empresa vinculada.',
        )

    # Instancia a classe Products passando o ID da empresa
    product_service = Products(current_user.empresa_id)

    # Busca o produto
    result = await product_service.search_product(product_name)

    return result


@product_deep_infos.get('/buscar-por-ticket')
async def search_products_by_tickets(
    current_user: SystemUser = Depends(get_current_user),
    type_ticket: str = Query(
        ..., description='Promoção, Novo, entre outros cadastrado.'
    ),
):

    product_service = Products(current_user.empresa_id)
    result = await product_service.observe_products_by_tickets(type_ticket)

    return result


@product_deep_infos.get('/ticket-medio')
async def average_ticket(current_user: SystemUser = Depends(get_current_user)):
    """
    Retorna valor medio do ticket de venda da empresa
    """

    product_service = Products(current_user.empresa_id)
    return await product_service.calculate_average_ticket()
