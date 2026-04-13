from datetime import datetime
from typing import Optional

from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import atomic

from src.controllers.car.cart_control import CartManagerDB
# Certifique-se de que os imports estão corretos
from src.controllers.sales.sales import Checkout
from src.model.product import Produto
from src.model.sale import Sales
from src.model.user import Usuario
from src.utils.sales_code_generator import gerar_codigo_venda


@atomic()
async def processar_venda_carrinho(
    user_id: int,  # Recebe o ID do usuário em vez do objeto completo
    cart_items: list,
    payment_method: str,
    employee_operator_id: int,
    customer_id: Optional[int] = None,
    installments: Optional[int] = None,
    cpf: Optional[str] = None,
    valor_recebido: Optional[float] = None,
    troco: Optional[float] = None,
    sale_code: Optional[
        str
    ] = None,  # 🔹 NOVO: Receber sale_code como parâmetro
) -> dict:
    """
    Processa todos os itens do carrinho em uma única transação
    """

    print('DEBUG: Iniciando processamento do carrinho...')
    print(
        f'DEBUG: user_id={user_id}, cart_items.len={len(cart_items)}, method={payment_method}'
    )

    itens_processados = []
    __saving_product_name = []
    total_geral = 0.0
    lucro_geral = 0.0
    cost_total_geral = 0.0
    produto_id = None

    if not cart_items:
        print('DEBUG: Carrinho está vazio, retornando falha.')
        return {'success': False, 'error': 'O carrinho está vazio.'}

    try:
        print(f'DEBUG: Buscando usuário com ID {user_id}...')
        # 🔹 Busca usuário dono da venda DENTRO da transação
        current_user = await Usuario.get_or_none(id=user_id)
        if not current_user:
            print(f'DEBUG: Erro: Usuário com ID {user_id} não encontrado.')
            raise Exception('Usuário não encontrado. processar_venda_carrinho')
        print(f'DEBUG: Usuário encontrado: {current_user.id}')

        # 🔹 CORREÇÃO: Gerar sale_code se não foi fornecido
        if not sale_code:
            sale_code = gerar_codigo_venda()  # len(6)
            print(f'DEBUG: 🔹 Sale_code gerado : {sale_code}')
        else:
            print(f'DEBUG: 🔹 Sale_code recebido: {sale_code}')

        # 🔹 Itera sobre cada item do carrinho
        for i, item in enumerate(cart_items):
            print(f'--- DEBUG: Iniciando processamento do Item {i+1} ---')

            # 1. Tentativa de obter dados do item
            is_dict = isinstance(item, dict)
            product_code = (
                item.get('product_code')
                if is_dict
                else getattr(item, 'product_code', None)
            )
            quantity = (
                int(item.get('quantity', 1))
                if is_dict
                else getattr(item, 'quantity', 1)
            )
            products_name = (
                item.get('product_name')
                if is_dict
                else getattr(item, 'product_name')
            )

            print(
                f'DEBUG Item {i+1}: Tipo={type(item)}, Code={product_code}, Qty={quantity}, Name={products_name}'
            )

            __saving_product_name.append({products_name})

            if not product_code:
                print(
                    f'DEBUG Item {i+1}: Pulando. product_code é None ou vazio.'
                )
                continue

            # 2. Busca do Produto no DB
            cleaned_code = product_code.strip().upper()
            print(
                f"DEBUG Item {i+1}: Buscando produto com Code='{cleaned_code}' e user_id={current_user.id}"
            )

            busca_produto = Q(usuario_id=current_user.id) & Q(
                product_code=cleaned_code
            )
            produto = await Produto.filter(busca_produto).first()

            if not produto:
                print(
                    f'DEBUG Item {i+1}: Pulando. Produto NÃO ENCONTRADO no DB.'
                )
                continue

            # 3. Verificar estoque
            stock_available = produto.stock or 0
            print(
                f'DEBUG Item {i+1}: Produto Encontrado. Estoque: {stock_available}, Solicitado: {quantity}'
            )

            if stock_available < int(quantity):
                print(f'DEBUG Item {i+1}: Pulando. Estoque insuficiente.')
                continue

            # 4. Atualizar estoque
            produto.stock -= int(quantity)
            produto.atualizado_em = datetime.now()
            await produto.save()
            print(
                f'DEBUG Item {i+1}: Estoque atualizado. Novo estoque: {produto.stock}'
            )

            # 5. Calcular valores
            sale_price = float(produto.sale_price or 0.0)
            cost_price = float(produto.cost_price or 0.0)
            produto_id = produto.id

            total_price = int(quantity) * sale_price
            lucro_total = (sale_price - cost_price) * int(quantity)
            cost_total = int(quantity) * cost_price

            # 6. Montar e adicionar item processado
            item_venda = {
                'product_name': produto.name,
                'quantity': int(quantity),
                'unit_price': sale_price,
                'total_price': total_price,
                'lucro_total': lucro_total,
                'cost_price': cost_price,
                'product_code': produto.product_code,
            }

            itens_processados.append(item_venda)
            total_geral += total_price
            lucro_geral += lucro_total
            cost_total_geral += cost_total

            print(
                f'DEBUG Item {i+1}: Item adicionado a itens_processados. Total parcial: {total_geral}'
            )

    except Exception as e:
        import traceback

        print(f'DEBUG ERRO FATAL NO LOOP: {str(e)}')
        print(traceback.format_exc())
        return {
            'success': False,
            'error': f'Erro interno ao processar itens do carrinho: processar_venda_carrinho {str(e)}',
        }

    print(
        f'DEBUG: Loop de processamento finalizado. Itens processados: {len(itens_processados)}'
    )

    if not itens_processados:
        print('DEBUG: Falha na validação final. Nenhum item processado.')
        return {
            'success': False,
            'error': f'Nenhum dos {len(cart_items)} itens pôde ser processado. processar_venda_carrinho',
        }

    # 🔹 7. Preparação dos dados para a Venda (Sales)
    print('DEBUG: Criando dados da Venda (Sales)...')
    venda_data = {
        'product_name': __saving_product_name,
        'quantity': len(itens_processados),
        'payment_method': payment_method.upper(),
        'total_price': total_geral,
        'lucro_total': lucro_geral,
        'cost_price': cost_total_geral,
        'produto_id': produto_id,
        'usuario_id': current_user.id,
        'funcionario_id': employee_operator_id,
        'customer_id': customer_id,
        'installments': installments,
        'valor_recebido': valor_recebido,
        'troco': troco,
        'sale_code': sale_code,  # 🔹 CORREÇÃO: Incluir sale_code nos dados da venda
    }

    # 🔹 8. Criar a venda no DB
    venda = await Sales.create(**venda_data)
    print(f'DEBUG: Venda (Sales) criada com ID: {venda.id}')

    # 🔹 9. Criar checkout instance
    checkout_instance = Checkout()
    checkout_instance._set_receipt_data(itens_processados)
    checkout_instance.total_price = total_geral
    checkout_instance.lucro_total = lucro_geral
    checkout_instance.payment_method = payment_method.upper()
    checkout_instance.venda = venda
    checkout_instance.sale_code = (
        sale_code  # 🔹 CORREÇÃO: Definir sale_code no checkout
    )
    print('DEBUG: Instância de Checkout criada e populada.')

    # 🔹 VERIFICAÇÃO: Confirmar que sale_code foi salvo
    venda_verificada = await Sales.get(id=venda.id)
    print(
        f'DEBUG: Venda verificada no DB: Sale_Code={venda_verificada.sale_code}'
    )

    # Limpar carrinho (comentado, mas bom saber)
    # await cart.limpar_carrinho(user_id=user_id)

    print('DEBUG: Retornando sucesso.')
    return {
        'success': True,
        'message': 'Venda processada com sucesso',
        'data': {
            'checkout_instance': checkout_instance,
            'total_venda': total_geral,
            'quantidade_itens': len(itens_processados),
            'itens_processados': itens_processados,
            'sale_code': sale_code,  # 🔹 CORREÇÃO: Retornar sale_code
            'venda_id': venda.id,
        },
    }
