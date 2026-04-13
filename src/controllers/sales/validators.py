from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status

from src.controllers.car.cart_control import CartManagerDB
from src.controllers.sales.sales import Checkout
from src.model.employee import Employees
from src.model.user import Usuario
from src.utils.sales_code_generator import gerar_codigo_venda


async def verify_datas(
    user_id: int,
    product_name: str,
    quantity: int,
    payment_method: str,
    valor_recebido: float | None = None,
    troco: float | None = None,
    installments: int | None = None,
    cpf: str | None = None,
    total_price: float | None = None,
) -> tuple[bool, float | None, int | None, float | None]:
    """
    Valida os dados básicos antes de processar a venda.

    Args:
        user_id (int): ID do usuário responsável.
        product_name (str): Nome do produto.
        quantity (int): Quantidade solicitada.
        payment_method (str): Método de pagamento (DINHEIRO, CARTAO, NOTA, PARCIAL).
        valor_recebido (float | None): Valor pago pelo cliente (quando aplicável).
        troco (float | None): Valor de troco (quando aplicável).
        installments (int | None): Parcelas no cartão.
        cpf (str | None): CPF do cliente (quando PARCIAL ou NOTA).
        total_price (float | None): Valor total da venda.

    Returns:
        tuple: (status: bool, troco: float | None, installments: int | None, valor_recebido: float | None)
    """

    # 🔹 Valida usuário
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Usuário inválido (verify_datas)',
        )

    # 🔹 Valida produto e quantidade
    if not product_name or not quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Informe todos os dados (verify_datas)',
        )

    # 🔹 Validações por forma de pagamento
    if payment_method.upper() == 'DINHEIRO':
        if valor_recebido is None or valor_recebido <= 0:
            raise HTTPException(
                status_code=400,
                detail='Valor recebido é obrigatório para pagamento em dinheiro (verify_datas)',
            )
        if troco is None:
            troco = 0.0

    if payment_method.upper() == 'CARTAO':
        if installments is None:
            installments = 1  # default para 1 parcela

    if payment_method.upper() == 'PARCIAL':
        if not cpf:
            raise HTTPException(
                status_code=400,
                detail='CPF é obrigatório para pagamento Parcial (verify_datas)',
            )
        if valor_recebido is None or valor_recebido <= 0:
            raise HTTPException(
                status_code=400,
                detail='Valor recebido é obrigatório para pagamento parcial (verify_datas)',
            )
        if total_price and valor_recebido > total_price:
            raise HTTPException(
                status_code=400,
                detail='Valor recebido não pode ser maior que o total (verify_datas)',
            )

    return True, troco, installments, valor_recebido


async def validating_information(
    current_user: Employees,
    payment_method: str,
    employee_operator_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    installments: Optional[int] = None,
    cpf: Optional[str] = None,
    valor_recebido: Optional[float] = None,
    troco: Optional[float] = None,
) -> dict:
    """
    Orquestra o fluxo de validação e registro de uma venda.

    Etapas principais:
        1. Valida se o usuário logado é funcionário.
        2. Obtém o admin associado ao funcionário.
        3. Recupera o carrinho de produtos.
        4. Aplica validações de acordo com a forma de pagamento.
        5. Cria instâncias de Checkout para cada produto do carrinho.
        6. Processa cada venda individualmente.
    """

    cart = CartManagerDB()

    try:
        # 🔹 1. Verifica se usuário é um funcionário
        employee = await Employees.filter(id=current_user.id).first()
        if not employee:
            return {
                'success': False,
                'message': 'Apenas funcionários podem realizar vendas',
            }

        employee_operator_id = employee.id
        employee_operator_name = employee.nome

        # 🔹 2. Busca o admin dono desse funcionário
        admin_user = await Usuario.get(id=employee.usuario_id)  # type: ignore
        if not admin_user:
            return {
                'success': False,
                'message': 'Usuário admin não encontrado',
            }

        # 🔹 3. Lista produtos no carrinho
        products = await cart.listar_produtos(employee_operator_id)
        if not products:
            return {'success': False, 'error': 'Carrinho vazio'}

        # 🔹 4. Validações específicas por método de pagamento
        if payment_method.upper() == 'DINHEIRO':
            if valor_recebido is None or valor_recebido <= 0:
                return {
                    'success': False,
                    'error': 'Valor recebido é obrigatório para pagamento em dinheiro',
                }
            if troco is None:
                troco = 0.0

        if payment_method.upper() == 'CARTAO' and installments is None:
            installments = 1  # Default: 1 parcela

        if payment_method.upper() == 'NOTA' and customer_id is None:
            return {
                'success': False,
                'error': 'Customer ID é obrigatório para venda em nota',
            }

        # 🔹 5. Preparação de variáveis para venda
        sale_total = 0.0
        sale_details = []
        for prod in products:
            sale_total += prod.total_price
            sale_details.append(
                {
                    'product_id': prod.product_id,
                    'product_name': prod.product_name,
                    'quantity': prod.quantity,
                    'unit_price': prod.price,
                }
            )

        # 🔹 6. Cria código de venda e inicializa variáveis
        sale_code = gerar_codigo_venda()
        invoice = []
        last_checkout_instance = None

        # 🔹 7. Cria instância de Checkout para cada produto e processa
        for prod in sale_details:
            checkout = Checkout(
                user_id=admin_user.id,
                product_name=prod['product_name'],
                produto_id=prod['product_id'],
                quantity=prod['quantity'],
                total_price=prod['quantity'] * prod['unit_price'],
                lucro_total=0.0,
                payment_method=payment_method.upper(),
                funcionario_id=employee_operator_id,
                funcionario_nome=employee_operator_name,
                sale_code=sale_code,
                customer_id=customer_id,
                installments=installments,
                valor_recebido=valor_recebido,
                troco=troco,
            )

            # 🔹 Processa a venda (estoque + registro + recibo)
            coupon, status = await checkout.process_sale(
                current_user=admin_user,
                product_code=str(prod['product_id']),
                quantity=prod['quantity'],
                payment_method=payment_method.upper(),
                funcionario_id=employee_operator_id,
                customer_id=customer_id,
                installments=installments,
                valor_recebido=valor_recebido,
                troco=troco,
            )

            if status:
                invoice.append(coupon)
                last_checkout_instance = checkout
            else:
                return {'success': False, 'error': 'Erro ao processar a venda'}

        from src.controllers.stoke.stoke_control import \
            gerar_relatorio_completo

        report = await gerar_relatorio_completo(admin_user.id)

        # 🔹 9. Resposta final
        return {
            'success': True,
            'data': {
                'notas_fiscais': invoice,
                'relatorio': report,
                'total_venda': sale_total,
                'codigo_da_venda': sale_code,
                'funcionario_operador_id': employee_operator_id,
                'funcionario_operador_nome': employee_operator_name,
                'admin_id': admin_user.id,
                'checkout_instance': last_checkout_instance,
                'customer_id': customer_id,
            },
            'error': None,
        }

    except Exception as e:
        # 🔹 Captura erros inesperados
        return {'success': False, 'error': str(e)}
