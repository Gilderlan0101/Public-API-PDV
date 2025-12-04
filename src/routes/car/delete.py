from fastapi import APIRouter, Depends, Query

from src.auth.deps import SystemUser, get_current_user
from src.auth.deps_employes import SystemEmployees, get_current_employee
from src.controllers.car.cart_control import CartManagerDB
from src.core.session_manager import get_session

router = APIRouter(tags=['Carrinho'])


@router.delete('/remover/{product_id}')
async def remover_produto(
    product_id: int,
    current_user: SystemEmployees = Depends(get_current_employee),
):
    """
    Remove um produto específico do carrinho.
    """

    empresa_id = current_user.empresa_id
    employee_id = current_user.id
    cart = CartManagerDB(company_id=empresa_id, employee_id=employee_id)
    return await cart.remove_produto(product_id)  # type: ignore


@router.delete('/limpar')
async def limpar_carrinho(
    current_user: SystemEmployees = Depends(get_current_employee),
):
    """
    Limpa todos os produtos do carrinho do usuário.
    """

    cart = CartManagerDB(
        company_id=current_user.empresa_id, employee_id=current_user.id
    )
    return await cart.limpar_carrinho()  # type: ignore


###################
#   DESATIVADA    #
###################

# @router.delete("/remover_por_venda")
# async def remover_produtos_por_venda(
#     sale_code: str = Query(
#         ..., description="Código da venda para remover produtos do carrinho"
#     ),
#     current_user: Usuario = Depends(get_current_user),
# ):
#     """
#     Remove produtos do carrinho baseado no código da venda.
#     Útil para devoluções ou trocas.
#     """
#     return await cart.remover_produtos_por_venda(sale_code)
