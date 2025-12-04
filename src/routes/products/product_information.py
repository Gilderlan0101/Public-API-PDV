from fastapi import APIRouter, Depends

from src.auth.deps import get_current_user
from src.controllers.products.monitoring_products import ProductInfo
from src.controllers.sales.sales_controller import (
    information_about_sales_and_products_and_employees,
)
from src.schemas.schema_user import SystemUser

list_products = APIRouter(prefix='/products', tags=['Produtos'])


@list_products.get('/por-categoria')
async def products_by_category(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Retorna todos os produtos do usuário separados por categoria.
    """
    product_info = ProductInfo(current_user.id)
    products = await product_info.get_products_by_category()
    return {'products': products}


@list_products.get('/quantidade-estoque')
async def quantity_in_stock(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Retorna a quantidade total de produtos em estoque do usuário.
    """
    product_info = ProductInfo(current_user.id)
    quantity = await product_info.count_products()
    return {'quantity': quantity}


@list_products.get('/valor-estoque')
async def total_stock_price(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Retorna o valor total de custo do estoque do usuário.
    """
    product_info = ProductInfo(current_user.id)
    total_price = await product_info.calculate_total_stock_price()
    return {'total_stock_price': total_price}


@list_products.get('/stoque-baixo')
async def low_stock(
    current_user: SystemUser = Depends(get_current_user),
) -> dict:
    """
    Retorna todos os produtos com estoque baixo
    """

    product_info = ProductInfo(current_user.id)
    all_products_witch_low_stock = await product_info.low_product_stock()
    return {'stokc': all_products_witch_low_stock}


@list_products.get('/informacao-geral-vendas')
async def informatios(current_user: SystemUser = Depends(get_current_user)):
    """
    Retona informação completa sobre vendas, quem vendeu, quantidade,data entre outras informaçoes
    """

    return await information_about_sales_and_products_and_employees(
        user_id=current_user.id
    )
