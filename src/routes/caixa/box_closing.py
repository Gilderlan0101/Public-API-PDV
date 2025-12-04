from fastapi import APIRouter, Body, Depends, HTTPException, status

from src.auth.deps import SystemUser, get_current_user
from src.controllers.caixa.cash_controller import CashController
from src.logs.infos import LOGGER
from src.model.caixa import Caixa
from src.model.user import Usuario

router = APIRouter()


@router.get('/fechamento/valores')
async def collection_of_the_day(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Buscando informaçoes sobre os caixas fechados
    """

    var = await CashController.get_caixa_details(current_user.id)

    return var


@router.post('/fechamento/{checkout_id}/{employe_id}')
async def closing_checkout(
    checkout_id: int,
    employe_id: int,
    current_user: SystemUser = Depends(get_current_user),
) -> dict:
    """closing_checkout: Rota usada pela empresa para fecha o caixa do funcionarios remotamente.

    Args:
        checkout_id: ID do caixa a ser fechado
        employe_id: ID do funcionário
    """

    try:
        # Attempt to close the checkout
        request = await CashController.close_checkout(
            employe_id=employe_id,
            checkout_id=checkout_id,
            company_id=current_user.empresa_id,
        )

        # If checkout was successfully closed
        if request:
            return {
                'status': 200,
                'msg': 'Caixa fechado com sucesso.',
                'caixa': request[0]['checkout_id'],
                'nome': request[0]['name'],
                'detalhes': request[0]['description'],
            }

        # If no checkout was found to close, return current checkout info
        user = await Usuario.filter(id=current_user.empresa_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Usuário não encontrado',
            )

        cash = await Caixa.filter(
            usuario_id=user.id, caixa_id=checkout_id
        ).first()

        if not cash:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Caixa com ID {checkout_id} não encontrado',
            )

        # Format the current balance
        saldo_formatado = f'{cash.saldo_atual:,.2f}'

        infos = {
            'status': 200,
            'message': 'Caixa encontrado mas não foi possível fechá-lo',
            'data': {
                'Nome': cash.nome,
                'ID': cash.id,
                'Caixa_id': cash.caixa_id,
                'Aberto': cash.aberto,
                'Saldo_atual': saldo_formatado,
            },
        }

        return infos

    except HTTPException:
        # Re-raise HTTP exceptions so they're handled properly by FastAPI
        raise
    except Exception as e:
        LOGGER.error(
            f'Erro na rota [CHECKOUT/FECHAMENTO]: {e} :: {e.__class__.__name__}'
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno do servidor ao processar o fechamento do caixa',
        )
