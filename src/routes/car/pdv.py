from fastapi import APIRouter, Depends

from src.auth.deps import SystemUser, get_current_user
from src.controllers.sales.separate_payment_methods import \
    separating_sales_by_payments

router = APIRouter()


@router.get('/completedsales')
async def result_sales(current_user: SystemUser = Depends(get_current_user)):

    return await separating_sales_by_payments(current_user.empresa_id)
