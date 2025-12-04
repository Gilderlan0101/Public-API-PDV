import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from src.auth.deps import SystemUser, get_current_user
from src.controllers.payments.pix import (
    GenerateQRCodeFor,
    PixCreateRequest,
    PixQRCodeResponse,
    PixService,
)
from src.schemas.payments.accounts_pix import (
    PixAccountResponse,
    PixAccountsList,
)

router = APIRouter()


@router.post('/create-pix', status_code=status.HTTP_201_CREATED)
async def create_pix_account(
    pix_data: PixCreateRequest,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Cria nova conta PIX para usuário autenticado
    """
    try:
        service = PixService(user_id=current_user.empresa_id)
        pix_account = await service.create_pix_account(pix_data)

        return {
            'message': 'Conta PIX criada com sucesso',
            'pix_id': pix_account.id,
            'key_pix': pix_account.key_pix,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao criar conta PIX',
        )


@router.post('/generate-qrcode', response_model=PixQRCodeResponse)
async def generate_pix_qrcode(
    pix_data: GenerateQRCodeFor,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Gera QR Code PIX dinâmico
    """
    try:
        service = PixService(user_id=current_user.empresa_id)
        return await service.generate_qr_code(pix_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao gerar QR Code',
        )


@router.get('/qrcode-file/{filename}')
async def get_qrcode_file(filename: str):
    """
    Serve arquivo de QR Code gerado
    """
    filepath = f'static/qrcodes/{filename}'

    if not os.path.exists(filepath):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Arquivo não encontrado',
        )

    return FileResponse(filepath, media_type='image/png', filename=filename)


@router.get('/accounts', response_model=PixAccountsList)
async def get_pix_accounts(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Retorna todas as contas PIX do usuário
    """
    try:
        service = PixService(user_id=current_user.empresa_id)
        accounts = await service.get_user_pix_accounts()

        return {'count': len(accounts), 'accounts': accounts}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao buscar contas PIX',
        )


@router.post('/select-pix')
async def account_default(
    select: int = Query(
        ..., description='ID da conta PIX a ser selecionada como padrão'
    ),
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Rota responsável por escolher uma conta pix padrão
    """
    try:
        # CORREÇÃO: usar current_user.id em vez de current_user.empresa_id
        service = PixService(user_id=current_user.empresa_id)

        # Chama o método para selecionar a conta
        selected_key = await service.select_account_default(
            select_an_account_id=select
        )

        return {
            'sucesso': True,
            'message': 'Conta PIX selecionada com sucesso',
            'chave_pix_selecionada': selected_key,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao selecionar conta PIX',
        )


@router.delete('/delete-account')
async def delete_pix(
    account: int = Query(..., description='ID da conta PIX a ser excluída'),
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Rota para realizar a remoção de uma conta pix
    """
    try:
        # CORREÇÃO: usar current_user.id em vez de current_user.empresa_id
        service = PixService(user_id=current_user.id)

        # CORREÇÃO: await faltante
        remove_account = await service.deactivate_pix_account(pix_id=account)

        if remove_account:
            return {'success': 200}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Falha ao excluir conta PIX',
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao excluir conta PIX',
        )
