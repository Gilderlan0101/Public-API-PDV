import asyncio

from src.model.sale import Sales


async def get_sales(user_id: int, sale_code: str):
    try:
        sales = await Sales.filter(
            usuario_id=user_id, sale_code=sale_code
        ).all()

        return sales
    except Exception as e:
        print(f'Erro em get_sales: {e}')
        return []
