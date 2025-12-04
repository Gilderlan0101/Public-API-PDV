# controller/delivery_reports.py

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from src.model.delivery import Delivery, DeliveryItem
from src.model.employee import Employees


async def gerenciagelivery(company_id: int) -> Dict[str, Any]:
    """
    Gerenciador de entregas: Responsável por gerenciar as corridas atribuídas aos funcionários do tipo 'Entregador'.

    Esta função:
    - Retorna todas as corridas com status 'esperando'
    - Atribui entregadores automagicamente às corridas pendentes
    - Emite alertas para corridas atrasadas
    - Gerencia o status dos entregadores

    Args:
        company_id (int): ID da empresa

    Returns:
        Dict[str, Any]: Dicionário com informações de entregas, entregadores e alertas
    """
    pending = []
    notice = []
    delivery_drivers_available = []
    delivery_drivers_busy = []
    status_delivery_man = ['Livre', 'Almoço', 'Inativo', 'Com entregas']
    timeout = timedelta(minutes=30)
    now = datetime.now(timezone.utc)

    try:
        # Buscando todas as corridas com status esperando
        search_for_pending_deliveries = await Delivery.filter(
            usuario_id=company_id, delivery_status='esperando'
        ).all()

        # Buscar todos os entregadores da empresa
        all_delivery_men = await Employees.filter(
            usuario_id=company_id, cargo='Entregador'
        ).all()

        # Classificar entregadores por status
        for delivery_man in all_delivery_men:
            # Verificar quantas entregas ativas o entregador tem
            active_deliveries = await Delivery.filter(
                usuario_id=company_id,
                assigned_to=delivery_man.nome,
                delivery_status__in=['em_andamento', 'a_caminho'],
            ).count()

            delivery_man_info = {
                'id': delivery_man.id,
                'nome': delivery_man.nome,
                'telefone': getattr(delivery_man, 'telefone', ''),
                'veiculo': getattr(delivery_man, 'veiculo', ''),
                'active_deliveries': active_deliveries,
            }

            if active_deliveries == 0:
                # Entregador livre
                delivery_man_info['status'] = status_delivery_man[0]  # Livre
                delivery_drivers_available.append(delivery_man_info)
            else:
                # Entregador ocupado
                delivery_man_info['status'] = status_delivery_man[
                    3
                ]  # Com entregas
                delivery_drivers_busy.append(delivery_man_info)

        # Processar entregas pendentes
        if search_for_pending_deliveries:
            for delivery in search_for_pending_deliveries:
                created_at = (
                    delivery.created_at.replace(tzinfo=timezone.utc)
                    if delivery.created_at.tzinfo is None
                    else delivery.created_at
                )
                atraso = (now - created_at) > timeout

                delivery_info = {
                    'delivery_id': delivery.id,
                    'address': delivery.address,
                    'customer_id': delivery.customer_id,
                    'payment_status': delivery.payment_status,
                    'delivery_status': delivery.delivery_status,
                    'delivery_type': delivery.delivery_type,
                    'assigned_to': delivery.assigned_to,
                    'total_price': delivery.total_price,
                    'created_at': created_at.isoformat(),
                    'atrasado': atraso,
                    'tempo_espera_minutos': int(
                        (now - created_at).total_seconds() / 60
                    ),
                }

                pending.append(delivery_info)

                if atraso:
                    notice.append(
                        {
                            'tipo': 'atraso',
                            'mensagem': f'Corrida #{delivery.id} para {delivery.address} está atrasada!',
                            'delivery_id': delivery.id,
                            'tempo_espera': f'{(now - created_at).total_seconds() / 60:.1f} minutos',
                        }
                    )

                # Atribuir entregador automaticamente se não tiver um atribuído
                if not delivery.assigned_to and delivery_drivers_available:
                    # Pegar o primeiro entregador disponível
                    assigned_driver = delivery_drivers_available[0]

                    # Atualizar a entrega com o entregador
                    delivery.assigned_to = assigned_driver['nome']
                    await delivery.save()

                    # Atualizar a informação na lista pendente
                    delivery_info['assigned_to'] = assigned_driver['nome']
                    delivery_info['assigned_driver_id'] = assigned_driver['id']

                    # Mover entregador para lista de ocupados
                    assigned_driver['status'] = status_delivery_man[
                        3
                    ]  # Com entregas
                    delivery_drivers_busy.append(assigned_driver)
                    delivery_drivers_available = delivery_drivers_available[1:]

                    notice.append(
                        {
                            'tipo': 'atribuicao',
                            'mensagem': f'Entregador {assigned_driver["nome"]} atribuído à corrida #{delivery.id}',
                            'delivery_id': delivery.id,
                            'driver_id': assigned_driver['id'],
                        }
                    )

        # Buscar entregas em andamento para monitoramento
        active_deliveries = await Delivery.filter(
            usuario_id=company_id,
            delivery_status__in=['em_andamento', 'a_caminho'],
        ).all()

        active_deliveries_info = []
        for delivery in active_deliveries:
            active_deliveries_info.append(
                {
                    'delivery_id': delivery.id,
                    'address': delivery.address,
                    'assigned_to': delivery.assigned_to,
                    'delivery_status': delivery.delivery_status,
                    'scheduled_time': delivery.scheduled_time.isoformat()
                    if delivery.scheduled_time
                    else None,
                    'total_price': delivery.total_price,
                }
            )

        # Estatísticas resumidas
        statistics = {
            'total_pending': len(pending),
            'total_active': len(active_deliveries_info),
            'total_drivers_available': len(delivery_drivers_available),
            'total_drivers_busy': len(delivery_drivers_busy),
            'total_notices': len(notice),
            'last_update': now.isoformat(),
        }

        return {
            'success': True,
            'statistics': statistics,
            'pending_deliveries': pending,
            'active_deliveries': active_deliveries_info,
            'available_drivers': delivery_drivers_available,
            'busy_drivers': delivery_drivers_busy,
            'notices': notice,
            'last_update': now.isoformat(),
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Erro ao gerenciar entregas: {str(e)}',
            'pending_deliveries': [],
            'active_deliveries': [],
            'available_drivers': [],
            'busy_drivers': [],
            'notices': [],
            'last_update': datetime.now(timezone.utc).isoformat(),
        }


# Funções auxiliares para gerenciamento específico
async def assign_delivery_to_driver(
    delivery_id: int, driver_id: int, company_id: int
) -> Dict[str, Any]:
    """
    Atribui uma entrega específica a um entregador.

    Args:
        delivery_id (int): ID da entrega
        driver_id (int): ID do entregador
        company_id (int): ID da empresa

    Returns:
        Dict[str, Any]: Resultado da operação
    """
    try:
        # Buscar entrega
        delivery = await Delivery.filter(
            id=delivery_id, usuario_id=company_id
        ).first()

        if not delivery:
            return {'success': False, 'error': 'Entrega não encontrada'}

        # Buscar entregador
        driver = await Employees.filter(
            id=driver_id, usuario_id=company_id, cargo='Entregador'
        ).first()

        if not driver:
            return {'success': False, 'error': 'Entregador não encontrado'}

        # Atribuir entregador à entrega
        delivery.assigned_to = driver.nome
        await delivery.save()

        return {
            'success': True,
            'message': f'Entregador {driver.nome} atribuído à entrega #{delivery_id}',
            'delivery_id': delivery_id,
            'driver_name': driver.nome,
            'driver_id': driver_id,
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Erro ao atribuir entregador: {str(e)}',
        }


async def update_delivery_status(
    delivery_id: int, new_status: str, company_id: int
) -> Dict[str, Any]:
    """
    Atualiza o status de uma entrega.

    Args:
        delivery_id (int): ID da entrega
        new_status (str): Novo status ('esperando', 'em_andamento', 'a_caminho', 'entregue', 'cancelado')
        company_id (int): ID da empresa

    Returns:
        Dict[str, Any]: Resultado da operação
    """
    try:
        valid_statuses = [
            'esperando',
            'em_andamento',
            'a_caminho',
            'entregue',
            'cancelado',
        ]

        if new_status not in valid_statuses:
            return {
                'success': False,
                'error': f'Status inválido. Use: {", ".join(valid_statuses)}',
            }

        delivery = await Delivery.filter(
            id=delivery_id, usuario_id=company_id
        ).first()

        if not delivery:
            return {'success': False, 'error': 'Entrega não encontrada'}

        delivery.delivery_status = new_status
        await delivery.save()

        return {
            'success': True,
            'message': f'Status da entrega #{delivery_id} atualizado para: {new_status}',
            'delivery_id': delivery_id,
            'new_status': new_status,
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Erro ao atualizar status: {str(e)}',
        }


async def get_driver_deliveries(
    driver_name: str, company_id: int
) -> Dict[str, Any]:
    """
    Obtém todas as entregas de um entregador específico.

    Args:
        driver_name (str): Nome do entregador
        company_id (int): ID da empresa

    Returns:
        Dict[str, Any]: Lista de entregas do entregador
    """
    try:
        deliveries = await Delivery.filter(
            usuario_id=company_id, assigned_to=driver_name
        ).all()

        deliveries_info = []
        for delivery in deliveries:
            deliveries_info.append(
                {
                    'delivery_id': delivery.id,
                    'address': delivery.address,
                    'delivery_status': delivery.delivery_status,
                    'payment_status': delivery.payment_status,
                    'total_price': delivery.total_price,
                    'created_at': delivery.created_at.isoformat(),
                    'scheduled_time': delivery.scheduled_time.isoformat()
                    if delivery.scheduled_time
                    else None,
                }
            )

        return {
            'success': True,
            'driver_name': driver_name,
            'total_deliveries': len(deliveries_info),
            'deliveries': deliveries_info,
        }

    except Exception as e:
        return {
            'success': False,
            'error': f'Erro ao buscar entregas do entregador: {str(e)}',
        }
    return {'pending': pending, 'notice': notice}


def race_designation():
    """
    race_designation: Responsável por designar de forma inteligente qual funcionário realizará a corrida.

    A função deve verificar se o funcionário já está em uma corrida ativa.
    Caso esteja, ela deve selecionar o próximo disponível na fila de entregadores.
    """
    pass
