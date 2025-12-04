import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.deps import SystemUser, get_current_user
from src.controllers.caixa.cash_controller import CashController
from src.model.caixa import Caixa
from src.model.user import Usuario

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get('/caixa/{caixa_id}/resumo')
async def resumo_caixa(
    caixa_id: int,
    current_user: SystemUser = Depends(get_current_user),
):
    """Retorna o resumo do caixa antes do fechamento."""

    logger.info(
        'Solicitando resumo do caixa',
        extra={'caixa_id': caixa_id, 'user_id': current_user.id},
    )

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Usuário não autenticado',
        )

    try:
        # Verifica se o caixa existe e pertence ao usuário
        caixa = await Caixa.filter(
            caixa_id=caixa_id, usuario_id=current_user.id
        ).first()
        if not caixa:
            logger.warning(
                'Caixa não encontrado', extra={'caixa_id': caixa_id}
            )
            raise HTTPException(
                status_code=404, detail='Caixa não encontrado.'
            )

        # Usa o método correto para obter os detalhes
        dados = await CashController.get_caixa_details(caixa_id)

        # Verifica se houve erro na obtenção dos dados
        if 'error' in dados:
            raise HTTPException(status_code=400, detail=dados['error'])

        logger.info(
            'Resumo do caixa gerado com sucesso', extra={'caixa_id': caixa_id}
        )

        return {
            'status': 200,
            'dados': dados,
            'valor_sugerido_fechamento': caixa.saldo_atual,
        }

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            'Erro ao gerar resumo do caixa',
            extra={'caixa_id': caixa_id, 'error': str(e)},
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail=str(e))
