from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.deps import SystemUser, get_current_user
from src.controllers.marketplace.product_search_service import (
    CustomerMarketplace,
)

marketplace = APIRouter()


@marketplace.get('/deep_search')
async def deep_search_of_products(
    product_name: str = Query(...),
    target_company: Optional[str] = None,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Realiza uma busca aprofundada por informações de um produto específico em outras empresas cadastradas no sistema.

    A pesquisa retorna dados relevantes como preços, fornecedores e demais informações comerciais do produto,
    podendo ser filtrada opcionalmente pelo nome da empresa desejada.
    """

    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Autenticação necessária para acessar esta funcionalidade',
        )

    deep_search = CustomerMarketplace(
        user_id=current_user.id,
        product_name=product_name,
        target_company=target_company,
    )
    return await deep_search.result()
