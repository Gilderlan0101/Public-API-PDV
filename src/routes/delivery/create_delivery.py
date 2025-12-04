import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.deps import SystemUser, get_current_user
from src.controllers.delivery.delivery_controller import CreateDelivery
from src.controllers.delivery.delivery_reports import (
    assign_delivery_to_driver,
    gerenciagelivery,
    get_driver_deliveries,
    update_delivery_status,
)
from src.controllers.delivery.delivery_status import (
    assign_specific_delivery,
    get_delivery_status_report,
    sales_quantity,
    total_sales,
    update_payments_status,
    update_race_status,
)
from src.schemas.delivery.schemas_delivery import DeliveryCreate

# TESTE REMOVE QUANDO ESTIVE TUDO OK
from src.utils.user_or_functional import i_request

# Configurar logging
logger = logging.getLogger(__name__)

# Criar router para delivery
delivery_router = APIRouter()


@delivery_router.get('/management')
@i_request
async def get_delivery_management(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para gerenciamento geral de delivery.
    Retorna todas as corridas pendentes, entregadores disponíveis e alertas.
    """
    try:
        result = await gerenciagelivery(company_id=current_user.id)
        return result

    except Exception as e:
        logger.error(f'Erro no gerenciamento de delivery: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.post('/create')
async def create_delivery(
    data: DeliveryCreate, current_user: SystemUser = Depends(get_current_user)
):
    """
    Endpoint para criar uma nova entrega.
    """
    try:
        # Criar instância do controller de delivery
        delivery_controller = CreateDelivery(
            customer_name=data.customer_name,
            customer_id=data.customer_id,
            address=data.address,
            items=data.items,
            delivery_type=data.delivery_type,
            scheduled_time=data.scheduled_time,
            cep=data.cep,
            number_of_bags=data.number_of_bags,
        )

        # Validar campos
        delivery_controller.verify_fields()

        # Verificar/registrar cliente
        await delivery_controller.check_if_cliente_is_registered(
            data.customer_id, current_user.id
        )

        # Adicionar entregador se especificado
        if data.delivery_man_id:
            await delivery_controller.add_delivery_man(
                current_user.id, data.delivery_man_id
            )

        # Criar registro da entrega
        result = await delivery_controller.create_delivery_record(
            current_user.id, current_user.id
        )

        return {
            'status': 200,
            'mensagem': 'Entrega criada com sucesso!',
            'delivery_data': result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Erro ao criar entrega: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@i_request
@delivery_router.post('/auto-assign')
async def auto_assign_deliveries(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para atribuição automática de entregas pendentes.
    """
    try:
        result = await update_race_status(company_id=current_user.id)
        return result

    except Exception as e:
        logger.error(f'Erro na atribuição automática: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.post('/assign')
async def assign_delivery_to_driver_route(
    delivery_id: int,
    driver_id: int,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para atribuir uma entrega específica a um entregador.
    """
    try:
        result = await assign_delivery_to_driver(
            delivery_id=delivery_id,
            driver_id=driver_id,
            company_id=current_user.id,
        )
        return result

    except Exception as e:
        logger.error(f'Erro ao atribuir entregador: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.post('/assign-specific')
async def assign_specific_delivery_route(
    delivery_id: int,
    driver_id: int,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para atribuição específica de uma entrega a um entregador.
    """
    try:
        result = await assign_specific_delivery(
            delivery_id=delivery_id,
            driver_id=driver_id,
            company_id=current_user.id,
        )
        return result

    except Exception as e:
        logger.error(f'Erro na atribuição específica: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.put('/status')
async def update_delivery_status_route(
    delivery_id: int,
    new_status: str,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para atualizar o status de uma entrega.
    """
    try:
        result = await update_delivery_status(
            delivery_id=delivery_id,
            new_status=new_status,
            company_id=current_user.id,
        )
        return result

    except Exception as e:
        logger.error(f'Erro ao atualizar status: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.get('/driver/{driver_name}')
async def get_driver_deliveries_route(
    driver_name: str, current_user: SystemUser = Depends(get_current_user)
):
    """
    Endpoint para obter todas as entregas de um entregador específico.
    """
    try:
        result = await get_driver_deliveries(
            driver_name=driver_name, company_id=current_user.id
        )
        return result

    except Exception as e:
        logger.error(f'Erro ao buscar entregas do entregador: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.get('/status-report')
async def get_delivery_status_report_route(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para relatório completo do status das entregas.
    """
    try:
        result = await get_delivery_status_report(company_id=current_user.id)
        return result

    except Exception as e:
        logger.error(f'Erro ao gerar relatório: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.put('/payment-status')
async def update_payment_status_route(
    sales_id: int,
    new_status: str,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para atualizar o status de pagamento de uma venda.
    """
    try:
        result = await update_payments_status(
            company_id=current_user.id,
            sales_id=sales_id,
            new_status=new_status,
        )
        return result

    except Exception as e:
        logger.error(f'Erro ao atualizar status de pagamento: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.get('/total-sales')
async def get_total_sales_route(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para calcular o total em reais de vendas no modo delivery.
    """
    try:
        result = await total_sales(company_id=current_user.id)
        return result

    except Exception as e:
        logger.error(f'Erro ao calcular total de vendas: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.get('/sales-quantity')
async def get_sales_quantity_route(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para exibir a quantidade de vendas realizadas no dia atual.
    """
    try:
        result = await sales_quantity(company_id=current_user.id)
        return result

    except Exception as e:
        logger.error(f'Erro ao buscar quantidade de vendas: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.get('/active-deliveries')
async def get_active_deliveries_route(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para buscar entregas ativas (em andamento e a caminho).
    """
    try:
        # Buscar dados de gerenciamento que incluem entregas ativas
        management_data = await gerenciagelivery(company_id=current_user.id)

        if management_data['success']:
            return {
                'success': True,
                'active_deliveries': management_data['active_deliveries'],
                'total_active': len(management_data['active_deliveries']),
                'timestamp': datetime.now().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=management_data.get(
                    'error', 'Erro ao buscar entregas ativas'
                ),
            )

    except Exception as e:
        logger.error(f'Erro ao buscar entregas ativas: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.get('/pending-deliveries')
async def get_pending_deliveries_route(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para buscar entregas pendentes.
    """
    try:
        # Buscar dados de gerenciamento que incluem entregas pendentes
        management_data = await gerenciagelivery(company_id=current_user.id)

        if management_data['success']:
            return {
                'success': True,
                'pending_deliveries': management_data['pending_deliveries'],
                'total_pending': len(management_data['pending_deliveries']),
                'timestamp': datetime.now().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=management_data.get(
                    'error', 'Erro ao buscar entregas pendentes'
                ),
            )

    except Exception as e:
        logger.error(f'Erro ao buscar entregas pendentes: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.get('/drivers')
async def get_drivers_route(
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Endpoint para buscar lista de entregadores.
    """
    try:
        # Buscar dados de gerenciamento que incluem entregadores
        management_data = await gerenciagelivery(company_id=current_user.id)

        if management_data['success']:
            return {
                'success': True,
                'available_drivers': management_data['available_drivers'],
                'busy_drivers': management_data['busy_drivers'],
                'total_available': len(management_data['available_drivers']),
                'total_busy': len(management_data['busy_drivers']),
                'timestamp': datetime.now().isoformat(),
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=management_data.get(
                    'error', 'Erro ao buscar entregadores'
                ),
            )

    except Exception as e:
        logger.error(f'Erro ao buscar entregadores: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


@delivery_router.get('/delivery/{delivery_id}')
async def get_delivery_details_route(
    delivery_id: int, current_user: SystemUser = Depends(get_current_user)
):
    """
    Endpoint para buscar detalhes de uma entrega específica.
    """
    try:
        # Buscar dados de gerenciamento
        management_data = await gerenciagelivery(company_id=current_user.id)

        if management_data['success']:
            # Procurar a entrega específica em todas as listas
            all_deliveries = (
                management_data['pending_deliveries']
                + management_data['active_deliveries']
            )

            delivery = next(
                (d for d in all_deliveries if d['delivery_id'] == delivery_id),
                None,
            )

            if delivery:
                return {'success': True, 'delivery': delivery}
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f'Entrega #{delivery_id} não encontrada',
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=management_data.get(
                    'error', 'Erro ao buscar detalhes da entrega'
                ),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Erro ao buscar detalhes da entrega: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno: {str(e)}',
        )


# Rota para health check do delivery
@delivery_router.get('/health')
async def delivery_health_check():
    """
    Endpoint para verificar se o serviço de delivery está funcionando.
    """
    return {
        'status': 'healthy',
        'service': 'delivery',
        'timestamp': datetime.now().isoformat(),
    }
