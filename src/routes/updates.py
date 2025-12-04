from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.auth.deps import SystemUser, get_current_user
from src.dasboard.sales import query_of_all_sales

allDatas = APIRouter()

# Modelo para cada item de venda individual
class SaleItem(BaseModel):
    id: int
    product_name: str
    quantity: int
    total_price: str
    lucro_total: str
    const_price: str
    sales_code: str
    payment_method: str
    created_at: Optional[str] = None

# Modelo principal da resposta do dashboard
class DashboardResponse(BaseModel):
    total_user_profit: str
    total_lucro: str
    sales_of_the_day: int
    total_items_sold_today: int
    total_sales_count_history: int
    sales: List[SaleItem]

@allDatas.get('/profit', response_model=DashboardResponse)
async def profit(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Rota que exibe metricas de vendas e lucro do dia (dashboard).
    """
    if not current_user.empresa_id:
        raise HTTPException(status_code=400, detail='Usuario invalido')

    query = await query_of_all_sales(company_id=current_user.empresa_id)

    if not query:
        raise HTTPException(status_code=404, detail='Nenhum dado encontrado')

    return query
