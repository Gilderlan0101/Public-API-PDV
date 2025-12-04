# routes/cart_update.py
from fastapi import APIRouter, Depends

from src.auth.deps import SystemUser, get_current_user
from src.controllers.car.cart_control import CartManagerDB
from src.core.session_manager import get_session
from src.schemas.carrinho import EditCartItem

router = APIRouter()


@router.post('/atualizar')
async def atualizar_item(
    item: EditCartItem,
    current_user: SystemUser = Depends(get_current_user),
):
    empresa_id = current_user.empresa_id
    employee_id = current_user.id

    cart = CartManagerDB(company_id=empresa_id, employee_id=employee_id)

    return await cart.update_produto(
        product_id=item.product_id,
        quantity=item.quantity,
        discount=item.discount,
        addition=item.addition,
        replace_quantity=item.replace_quantity,
        replace_discount=item.replace_discount,
        replace_addition=item.replace_addition,
    )
