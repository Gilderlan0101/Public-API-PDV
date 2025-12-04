# controller/delivery_controller.py
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Depends, HTTPException, status

from src.auth.deps import SystemUser, get_current_user
from src.model.customers import Customer
from src.model.delivery import Delivery, DeliveryItem
from src.model.employee import Employees
from src.schemas.delivery.schemas_delivery import DeliveryCreate


class CreateDelivery:
    """
    Classe responsável por criar uma entrega.

    Gerencia a validação de dados, verificação de clientes e preparação
    de informações para o processo de entrega.

    Args:
        customer_name (str): Nome do cliente (opcional)
        customer_id (int): ID do cliente no sistema (opcional)
        address (Dict): Dicionário com componentes do endereço
        items (list): Lista de produtos/items para entrega
        delivery_type (str): Tipo de veículo para entrega
        scheduled_time (Optional[datetime]): Horário máximo para entrega
        cep (str): CEP do endereço (opcional)
        number_of_bags (int): Quantidade de sacolas
    """

    def __init__(
        self,
        customer_name: str,
        customer_id: Optional[int] = None,
        address: Dict[str, str] = None,
        items: list = None,
        delivery_type: str = None,
        scheduled_time: Optional[datetime] = None,
        cep: Optional[str] = None,
        number_of_bags: int = None,
    ):

        self.customer_name = customer_name
        self.customer_id = customer_id
        self.address = address or {}
        self.items = items or []
        self.scheduled_type = delivery_type
        self.scheduled_time = scheduled_time
        self.cep = cep
        self.number_of_bags = number_of_bags

        # Estrutura base para informações do cliente
        self.customer_information = [
            {
                'full_name': '',
                'house_number': '',
                'neighborhood': '',
                'city': '',
                'state': '',
                'cep': '',
                'address_string': '',
                'number_of_bags': '',
                'assigned_to': '',
                'items': [],
            }
        ]

    def verify_fields(self) -> bool:
        """
        Valida todos os campos obrigatórios antes de processar a entrega.

        Returns:
            bool: True se todos os campos são válidos

        Raises:
            HTTPException: Se algum campo obrigatório estiver inválido ou faltando
        """
        # Validação de itens
        if not self.items or len(self.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Adicione produtos ao pedido antes de iniciar a entrega.',
            )

        # Validação de endereço
        if not self.address or not isinstance(self.address, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Endereço de entrega é obrigatório e deve ser um dicionário.',
            )

        # Verifica campos mínimos do endereço
        required_address_fields = ['street', 'neighborhood', 'city']
        for field in required_address_fields:
            if not self.address.get(field):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Campo '{field}' do endereço é obrigatório.",
                )

        # Validação do tipo de veículo
        valid_vehicle_types = ['moto', 'carro']
        if (
            not self.scheduled_type
            or self.scheduled_type not in valid_vehicle_types
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de veículo é obrigatório. Escolha entre: {', '.join(valid_vehicle_types)}",
            )

        return True

    def _format_address_string(self) -> str:
        """
        Formata o endereço dict em string para exibição.

        Returns:
            str: Endereço formatado como string
        """
        parts = [
            self.address.get('street', ''),
            self.address.get('house_number', ''),
            self.address.get('neighborhood', ''),
            self.address.get('city', ''),
            self.address.get('state', ''),
        ]
        return ', '.join([part for part in parts if part])

    async def check_if_cliente_is_registered(
        self, customer: Optional[int] = None, company_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Verifica se o cliente já existe no banco de dados da loja.

        Se existir, preenche automaticamente os campos com os dados dele.
        Caso não exista, preencha os campos com as informações solicitadas na classe.

        Args:
            customer (int): ID do cliente para busca
            company_id (int): ID da empresa/loja

        Returns:
            List[Dict[str, Any]]: Lista com informações do cliente

        Raises:
            HTTPException: Se ocorrer erro durante a busca
        """
        # Valida campos obrigatórios primeiro
        self.verify_fields()

        try:
            # Consultar cliente pelo ID informado (se fornecido)
            if customer and company_id:
                search_cliente = await Customer.filter(
                    usuario_id=company_id, id=customer
                ).first()
            else:
                search_cliente = None

            if search_cliente:
                # Cliente encontrado - preenche com dados do banco
                fields = [
                    'full_name',
                    'house_number',
                    'neighborhood',
                    'city',
                    'state',
                    'cep',
                ]
                self.customer_information[0] = {
                    field: getattr(search_cliente, field, '') or ''
                    for field in fields
                }
                # Adiciona campos específicos da entrega
                self.customer_information[0]['items'] = self.items
                self.customer_information[0][
                    'number_of_bags'
                ] = self.number_of_bags
                self.customer_information[0][
                    'address_string'
                ] = self._format_address_string()

            else:
                # Cliente não encontrado - usa informações do dicionário address
                self.customer_information[0]['full_name'] = (
                    self.customer_name or ''
                )
                self.customer_information[0][
                    'house_number'
                ] = self.address.get('house_number', '')
                self.customer_information[0][
                    'neighborhood'
                ] = self.address.get('neighborhood', '')
                self.customer_information[0]['city'] = self.address.get(
                    'city', ''
                )
                self.customer_information[0]['state'] = self.address.get(
                    'state', 'BA'
                )
                self.customer_information[0][
                    'cep'
                ] = self.cep or self.address.get('cep', '')
                self.customer_information[0][
                    'address_string'
                ] = self._format_address_string()
                self.customer_information[0]['items'] = self.items
                self.customer_information[0][
                    'number_of_bags'
                ] = self.number_of_bags

            return self.customer_information

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Erro ao buscar informações do cliente: {str(e)}',
            )

    async def add_delivery_man(
        self,
        company_id: Optional[int] = None,
        delivery_man_id: Optional[int] = None,
    ) -> None:
        """
        Adiciona o entregador responsável pela entrega.

        Args:
            company_id (int): ID da empresa
            delivery_man_id (int): ID do entregador

        Raises:
            HTTPException: Se o entregador não for encontrado ou ocorrer erro
        """
        if company_id and delivery_man_id:
            try:
                search_employee = await Employees.filter(
                    usuario_id=company_id, id=delivery_man_id
                ).first()

                if search_employee:
                    self.customer_information[0][
                        'assigned_to'
                    ] = search_employee.nome
                else:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail='Entregador não encontrado.',
                    )

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f'Erro ao adicionar entregador: {str(e)}',
                )

    async def create_delivery_record(
        self, company_id: int, user_id: int
    ) -> Dict[str, Any]:
        """
        Cria o registro completo de entrega no banco de dados.

        Args:
            company_id (int): ID da empresa
            user_id (int): ID do usuário responsável

        Returns:
            Dict[str, Any]: Registro da entrega criada
        """
        try:
            # Verifica se já temos as informações do cliente
            if not self.customer_information[0]['full_name']:
                await self.check_if_cliente_is_registered(
                    self.customer_id, company_id
                )

            # Primeiro cria o registro principal da entrega
            delivery_data = {
                'usuario_id': user_id,
                'customer_id': self.customer_id,
                'address': self.customer_information[0]['address_string'],
                'latitude': None,  # Pode ser calculado depois
                'longitude': None,  # Pode ser calculado depois
                'total_distance_km': 0.0,  # Pode ser calculado depois
                'delivery_fee': 0.0,  # Pode ser calculado depois
                'total_price': 0.0,  # Precisa ser calculado baseado nos items
                'payment_status': 'Pendente',
                'delivery_status': 'esperando',
                'delivery_type': self.scheduled_type,
                'assigned_to': self.customer_information[0].get('assigned_to'),
                'scheduled_time': self.scheduled_time,
                'created_at': datetime.now(),
            }

            # Calcula preço total baseado nos items
            total_price = self._calculate_total_price()
            delivery_data['total_price'] = total_price

            # Cria registro principal da entrega
            delivery_record = await Delivery.create(**delivery_data)

            # Cria os itens da entrega
            await self._create_delivery_items(delivery_record.id)

            return {
                'delivery_id': delivery_record.id,
                'customer_info': {
                    'name': self.customer_information[0]['full_name'],
                    'address': self.customer_information[0]['address_string'],
                    'is_registered': bool(self.customer_id),
                },
                'delivery_info': {
                    'vehicle_type': self.scheduled_type,
                    'items_count': len(self.items),
                    'number_of_bags': self.number_of_bags,
                    'scheduled_time': self.scheduled_time,
                    'total_price': total_price,
                },
                'status': 'created',
                'created_at': (
                    delivery_record.created_at.isoformat()
                    if hasattr(delivery_record.created_at, 'isoformat')
                    else str(delivery_record.created_at)
                ),
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Erro ao criar registro de entrega: {str(e)}',
            )

    def _calculate_total_price(self) -> float:
        """
        Calcula o preço total da entrega baseado nos items.

        Returns:
            float: Preço total calculado
        """
        total = 0.0
        for item in self.items:
            # Assumindo que cada item é um dict com 'price' e 'quantity'
            if (
                isinstance(item, dict)
                and 'price' in item
                and 'quantity' in item
            ):
                total += item['price'] * item['quantity']
            elif hasattr(item, 'price') and hasattr(item, 'quantity'):
                total += item.price * item.quantity
            else:
                # Se não tem preço definido, adiciona um valor padrão
                total += 10.0  # Preço padrão para itens sem preço definido

        return total

    async def _create_delivery_items(self, delivery_id: int) -> None:
        """
        Cria os registros dos itens da entrega.

        Args:
            delivery_id (int): ID da entrega principal
        """
        try:
            for item in self.items:
                item_data = {
                    'delivery_id': delivery_id,
                    'product_id': item.get('product_id', 0),
                    'quantity': item.get('quantity', 1),
                    'price': item.get('price', 0.0),
                }
                await DeliveryItem.create(**item_data)

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Erro ao criar itens da entrega: {str(e)}',
            )
