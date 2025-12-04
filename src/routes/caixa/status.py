import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.auth.deps import SystemUser, get_current_user
from src.controllers.caixa.cash_controller import CashController
from src.model.caixa import Caixa
from src.model.user import Usuario
from src.utils.user_or_functional import i_request

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get('/status')
async def get_caixa_status(
    current_user: SystemUser = Depends(get_current_user),
    funcionario_id: Optional[int] = Query(
        None, description='ID do funcionário para verificar caixa'
    ),
):
    """
    Verifica se há caixa aberto para o usuário/funcionário
    """
    logger.debug(
        'Verificando status do caixa',
        extra={
            'user_id': current_user.id,
            'funcionario_id_solicitado': funcionario_id,
        },
    )

    try:
        target_funcionario_id = (
            funcionario_id if funcionario_id else current_user.id
        )

        caixa_aberto = await CashController.get_caixa_aberto_funcionario(
            usuario_id=current_user.id, funcionario_id=target_funcionario_id
        )

        if not caixa_aberto:
            caixa_aberto = await Caixa.filter(
                usuario_id=current_user.empresa_id or current_user.id,
                aberto=True,
            ).first()

        status_info = {
            'aberto': caixa_aberto is not None,
            'caixa': caixa_aberto,
            'funcionario_id': target_funcionario_id,
            'mensagem': 'Caixa aberto encontrado'
            if caixa_aberto
            else 'Nenhum caixa aberto encontrado',
        }

        logger.debug(
            'Status do caixa verificado',
            extra={
                'aberto': status_info['aberto'],
                'funcionario_id': target_funcionario_id,
            },
        )

        return status_info

    except Exception as e:
        logger.error(
            'Erro ao verificar status do caixa',
            extra={'error': str(e), 'user_id': current_user.id},
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f'Erro ao verificar status do caixa: {str(e)}',
        )
