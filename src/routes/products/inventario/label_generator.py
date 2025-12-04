# Arquivo: src/routes/products/inventario/label_generator.py

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.deps import SystemUser, get_current_user
from src.controllers.products.inventario.generetor_label import LabelGenerator
from src.routes.products.inventario.stock_entry_controller import (
    inventory_router,
)


# Usando o router de inventário já definido para o endpoint
@inventory_router.post('/gerar-etiquetas', status_code=status.HTTP_200_OK)
async def create_label(
    product_code: str = Query(
        ..., description='Codigo do produto que vai receber uma label | tag'
    ),
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Gera um código de barras/lote único e o registra no campo 'label' do produto
    associado à empresa do usuário logado.
    """
    try:
        # Define o ID da empresa. Se for funcionário, usa empresa_id; se for dono, usa o próprio ID.
        company_id = (
            current_user.empresa_id
            if current_user.empresa_id
            else current_user.id
        )

        # 1. Instancia o gerador de rótulos com os dados necessários
        label_gen = LabelGenerator(
            company_id=company_id,
            product_code=product_code,
            # product_id é deixado como None
        )

        # 2. Executa a lógica de busca, geração de código e atualização do DB
        # A lógica de tratamento de erro (404) está contida dentro da classe.
        result = await label_gen.create_label_by_product()

        return {
            'success': True,
            'message': f"Rótulo '{result['label']}' gerado e registrado com sucesso para o produto: {result['product_name']}",
            'data': result,
        }

    except HTTPException as e:
        # Repassa exceções HTTP (ex: 404 Not Found, 500 Interno)
        raise e
    except Exception as e:
        # Trata erros inesperados como 500
        print(f'Erro inesperado ao gerar rótulo: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno ao processar a geração de rótulo: {str(e)}',
        )
