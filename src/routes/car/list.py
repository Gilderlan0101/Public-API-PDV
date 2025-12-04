from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.deps_employes import SystemEmployees, get_current_employee
from src.controllers.car.cart_control import CartManagerDB

# O uso de get_session não é necessário, pois a autenticação JWT já provê os dados
# from src.core.session_manager import get_session

router = APIRouter(tags=['Carrinho'])


@router.get('/')
async def listar_carrinho(
    # Obtém os dados da sessão (empresa_id, employee_id) via JWT
    current_user: SystemEmployees = Depends(get_current_employee),
):
    """
    [ATENÇÃO: ROTA DO CARRINHO] Retorna os itens do carrinho (cart items)
    associados ao caixa ativo do funcionário.

    Se você deseja a lista COMPLETA de produtos para venda, use a rota /list.
    """

    # 1. Extrair IDs da dependência JWT (garantido de estar correto e ativo)
    empresa_id = current_user.empresa_id
    employee_id = current_user.id

    if not empresa_id or not employee_id:
        # Failsafe para garantir que o JWT retornou os dados essenciais
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Sessão JWT inválida ou incompleta. Faça login novamente.',
        )

    # 2. Inicializar o CartManagerDB
    # O CartManagerDB usa estes IDs para buscar o caixa ativo.
    cart = CartManagerDB(company_id=empresa_id, employee_id=employee_id)

    # 3. Chamar a lógica de listagem (lista os itens NO CARRINHO)
    return await cart.listar_produtos()
