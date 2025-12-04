import logging
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from src.auth.deps import SystemUser, get_current_user
from src.controllers.payments.partial.create_depts import Person
from src.controllers.payments.partial.process_partial_payments import (
    PartialPayment,
)
from src.controllers.payments.partial.views_depts import ViewsAllDepts
from src.model.partial import Partial, finished_debts
from src.routes.customer.customer_registration import customers
from src.schemas.payments.payment_methods import (
    RegisterUserForPartialMode,
    VendaParcialData,
)

# Configuração de logging
LOGGER = logging.getLogger(__name__)


class DebtUpdateData(BaseModel):
    """Schema para atualização de dívida"""

    cpf: str
    value_received: float
    type_meyhod_payment: str


@customers.post('/cadastra-cliente-partial')
async def create_partial_customer(
    data: RegisterUserForPartialMode,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para cadastrar cliente para pagamentos parciais
    """
    try:
        # Valida e limpa dados do cliente
        clean_cpf = data.cpf.replace('.', '').replace('-', '')
        if len(clean_cpf) != 11:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='CPF deve conter 11 dígitos',
            )

        clean_phone = (
            data.tel.replace('(', '')
            .replace(')', '')
            .replace(' ', '')
            .replace('-', '')
        )

        # Verifica se cliente já existe
        existing_customer = await Partial.filter(
            cpf=clean_cpf, usuario_id=current_user.empresa_id
        ).first()

        if existing_customer:
            # Atualiza cliente existente
            await Partial.filter(
                cpf=clean_cpf, usuario_id=current_user.empresa_id
            ).update(
                customers_name=data.full_name,
                tel=clean_phone,
                produto=data.produto,
            )
            message = 'Cliente atualizado com sucesso'
            LOGGER.info(f'Cliente {data.full_name} atualizado')
        else:
            # Cria novo cliente
            await Partial.create(
                usuario_id=current_user.empresa_id,
                customers_name=data.full_name,
                cpf=clean_cpf,
                tel=clean_phone,
                produto=data.produto,
                value=0.0,
                payment_method=None,
            )
            message = 'Cliente cadastrado com sucesso'
            LOGGER.info(f'Cliente {data.full_name} criado')

        return {
            'status': 200,
            'mensagem': message,
            'name': data.full_name,
            'tel': data.tel,
            'cpf': clean_cpf,
            'produto': data.produto,
        }

    except HTTPException:
        raise
    except Exception as error:
        LOGGER.error(f'Erro ao cadastrar cliente: {str(error)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao cadastrar cliente',
        )


@customers.post('/registra-venda')
async def register_partial_sale(
    data: VendaParcialData,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para registrar venda parcial
    """
    try:
        # Validação do CPF
        clean_cpf = data.cpf.replace('.', '').replace('-', '')
        if len(clean_cpf) != 11:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail='CPF inválido'
            )

        # Valida valor recebido
        if data.valor_recebido > data.valor_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Valor recebido não pode ser maior que valor total',
            )

        # Calcula saldo devedor
        remaining_debt = data.valor_total - data.valor_recebido

        # Busca cliente
        customer = await Partial.filter(
            cpf=clean_cpf, usuario_id=current_user.empresa_id
        ).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Cliente não encontrado. Cadastre o cliente primeiro.',
            )

        # Atualiza dados do cliente com a venda
        await Partial.filter(
            cpf=clean_cpf, usuario_id=current_user.empresa_id
        ).update(
            value=remaining_debt,
            payment_method=data.metodo_pagamento,
            produto=data.produto,
            date=datetime.now(ZoneInfo('America/Sao_Paulo')),
        )

        # Se dívida foi totalmente paga, move para histórico
        if remaining_debt <= 0:
            updated_customer = await Partial.filter(
                cpf=clean_cpf, usuario_id=current_user.empresa_id
            ).first()

            await finished_debts.create(
                usuario_id=current_user.empresa_id,
                name=updated_customer.customers_name,
                tel=updated_customer.tel,
                product_name=data.produto,
                value=data.valor_total,
                payments={
                    'payment_method': data.metodo_pagamento,
                    'paid_value': data.valor_recebido,
                    'date': datetime.now(
                        ZoneInfo('America/Sao_Paulo')
                    ).isoformat(),
                },
            )

            # Remove da tabela de dívidas ativas
            await Partial.filter(
                cpf=clean_cpf, usuario_id=current_user.empresa_id
            ).delete()
            LOGGER.info(f'Dívida quitada para CPF: {clean_cpf}')

        LOGGER.info(f'Venda registrada para CPF: {clean_cpf}')

        return {
            'status': 200,
            'mensagem': 'Venda parcial registrada com sucesso',
            'cpf': clean_cpf,
            'valor_recebido': data.valor_recebido,
            'saldo_devedor': remaining_debt,
            'produto': data.produto,
            'status_divida': 'quitada' if remaining_debt <= 0 else 'pendente',
        }

    except HTTPException:
        raise
    except Exception as error:
        LOGGER.error(f'Erro ao registrar venda parcial: {str(error)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao registrar venda',
        )


@customers.get('/dividas-atual')
async def get_current_debts(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para buscar dívidas atuais do usuário
    """
    var = ViewsAllDepts(company_id=current_user.empresa_id)
    return await var.get_current_debts()


@customers.get('/dividas-pagas')
async def get_paid_debts(current_user: SystemUser = Depends(get_current_user)):
    """
    Endpoint para buscar histórico de dívidas pagas
    """
    var = ViewsAllDepts(company_id=current_user.empresa_id)
    return await var.get_paid_debts()


# @customers.put('/atualiza-valor')
# async def update_debt_value(
#     data: DebtUpdateData,
#     current_user: SystemUser = Depends(get_current_user)
# ):
#     """
#     Endpoint para atualizar valor da dívida (registrar pagamento)
#     """
#     try:
#         valid_payment_methods = ['PIX', 'CARTÂO', 'CARTAO', 'PARCIAL', 'DINHEIRO']

#         if data.type_meyhod_payment.upper() not in [method.upper() for method in valid_payment_methods]:
#             raise HTTPException(
#                 status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
#                 detail="Selecione uma forma de pagamento válida"
#             )

#         LOGGER.info(f"Iniciando pagamento de dívida [PARCIAL]")
#         LOGGER.info(f"Metodo pagamento [{data.type_meyhod_payment}]")

#         # Processa pagamento
#         payment_processor = PartialPayment(
#             payment_method=data.type_meyhod_payment,
#             value_received=data.value_received,
#             cpf=data.cpf,
#             user_id=current_user.id  # Usa ID do usuário atual
#         )

#         result = await payment_processor.update_value()

#         LOGGER.info("Pagamento realizado com sucesso")

#         return result

#     except HTTPException:
#         raise
#     except Exception as error:
#         LOGGER.error(f"Erro ao atualizar dívida [route]: {str(error)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erro interno ao processar pagamento {str(error)}"
#         )


@customers.delete('/deleta-todas-as-dividas')
async def delete_all_debts(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para deletar TODAS as dívidas do usuário
    ATENÇÃO: Esta operação é irreversível
    """
    try:
        LOGGER.warning(
            f'Usuário {current_user.id} iniciando deleção de TODAS as dívidas'
        )

        # Deleta dívidas pagas (histórico)
        paid_debts_deleted = await finished_debts.filter(
            usuario_id=current_user.id
        ).delete()

        # Deleta dívidas atuais
        current_debts_deleted = await Partial.filter(
            usuario_id=current_user.id
        ).delete()

        LOGGER.warning(
            f'Deleção concluída: '
            f'{paid_debts_deleted} dívidas pagas e '
            f'{current_debts_deleted} dívidas atuais removidas'
        )

        return {
            'status': 200,
            'mensagem': 'Todas as dívidas foram deletadas com sucesso',
            'detalhes': {
                'dividas_pagas_removidas': paid_debts_deleted,
                'dividas_atuais_removidas': current_debts_deleted,
            },
        }

    except Exception as error:
        LOGGER.error(f'Erro ao deletar dívidas: {str(error)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao deletar dívidas',
        )
