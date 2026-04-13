# Arquivo: src/routes/products/inventario/stock_exit_controller.py

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.deps import SystemUser, get_current_user
# 💡 Importação da classe de controle de saída de estoque
from src.controllers.products.inventario.stoke_exit import StockExit
from src.routes.products.inventario.stock_entry_controller import \
    inventory_router


# Usando o router de inventário já definido
@inventory_router.post('/gerar-saida-produtos', status_code=status.HTTP_200_OK)
async def stock_exit_products(
    action: str = Query(
        ...,
        description="Ação a ser executada: 'partial' (baixa de quantidade) ou 'total' (remoção/arquivamento total).",
    ),
    product_code: Optional[str] = Query(
        None, description='Código do produto.'
    ),
    product_name: Optional[str] = Query(
        None, description='Nome do produto (alternativa ao código).'
    ),
    quantity_to_remove: int = Query(
        0,
        description="Quantidade a ser removida (obrigatório para action='partial').",
    ),
    detail: Annotated[
        Optional[str],
        Query(description='Descrição/motivo da saída ou arquivamento.'),
    ] = None,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Processa a saída de produtos do estoque, seja por baixa parcial ou arquivamento total.
    """
    try:
        # Define o ID da empresa
        company_id = (
            current_user.empresa_id
            if current_user.empresa_id
            else current_user.id
        )

        # 1. Instancia a classe de controle
        stock_exit = StockExit(
            company_id=company_id,
            product_code=product_code,
            product_name=product_name,
            quantity_to_remove=quantity_to_remove,
            detail=detail,
        )

        # 2. Executa a ação baseada no parâmetro 'action'
        if action.lower() == 'partial':
            # Baixa parcial exige quantidade > 0
            if quantity_to_remove <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A ação 'partial' requer 'quantity_to_remove' maior que zero.",
                )

            return await stock_exit.remove_quantity()

        elif action.lower() == 'total':
            # Remoção total exige um motivo no 'detail'
            if not detail:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A ação 'total' requer um 'detail' (motivo) para arquivamento.",
                )

            return await stock_exit.remove_product_total()

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ação inválida. Use 'partial' ou 'total'.",
            )

    except HTTPException as e:
        # Repassa exceções HTTP (ex: 400, 404, 401)
        raise e
    except Exception as e:
        # Trata erros inesperados como 500
        print(f'Erro inesperado no controlador de saída de estoque: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno ao processar a saída de estoque: {str(e)}',
        )
