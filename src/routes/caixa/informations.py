from fastapi import APIRouter, Depends

from src.auth.deps import SystemUser, get_current_user
from src.logs.infos import LOGGER
from src.model.caixa import Caixa
from src.model.user import Usuario

router = APIRouter()


@router.get('/infos/caixas')
async def information_from_all_cashiers(
    current_user: SystemUser = Depends(get_current_user),
):
    """Retorna informações de todos os caixas do usuário"""

    LOGGER.debug(
        'Listando caixas do usuário', extra={'user_id': current_user.id}
    )

    if not current_user.id:
        raise HTTPException(status_code=404, detail='Usuario não encontrado.')

    user = await Usuario.filter(id=current_user.empresa_id).first()
    cashs = await Caixa.filter(usuario_id=user.id).all()

    infos = []
    for data in cashs:

        saldo_formatado = f'{data.saldo_atual:,.2f}'
        caixa_info = {
            'Nome': data.nome,
            'ID': data.id,
            'Caixa_id': data.caixa_id,  # Make sure this field exists
            'Aberto': data.aberto,
            'Saldo_atual': saldo_formatado,
        }
        # Debug: log each caixa info
        LOGGER.debug(f'Caixa info: {caixa_info}')
        infos.append(caixa_info)

    LOGGER.debug(
        'Caixas listados',
        extra={'total_caixas': len(cashs), 'caixas_abertos': len(infos)},
    )

    # Debug: log the final response
    LOGGER.debug(f'Final response: {infos}')

    return infos
