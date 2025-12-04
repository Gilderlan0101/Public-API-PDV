from typing import Optional

from src.model.product import Produto
from src.model.sale import Sales


async def delete_or_update_sale(
    user_id: int, sale_id: int, new_quantity: Optional[int] = None
):
    """
    Atualiza ou deleta uma venda específica da tabela Sales.

    - Se new_quantity for informado:
        - Atualiza a quantidade da venda.
        - Recalcula total_price e lucro_total.
        - Ajusta o estoque do produto corretamente.
    - Se new_quantity for None:
        - Deleta a venda.
        - Devolve a quantidade total ao estoque do produto.
    """
    try:
        # Busca a venda pelo ID da venda (não do produto)
        sale = await Sales.filter(usuario_id=user_id, id=sale_id).first()
        if not sale:
            return {'status': 404, 'msg': 'Venda não encontrada.'}

        # Busca o produto relacionado à venda
        produto = await Produto.get(id=sale.produto_id)  # type: ignore

        if new_quantity is not None:
            # Guarda quantidade antiga
            old_quantity = sale.quantity

            # Atualiza quantidade, total_price e lucro
            sale.quantity = new_quantity
            sale.total_price = new_quantity * produto.sale_price
            sale.lucro_total = new_quantity * (
                produto.sale_price - produto.cost_price
            )
            await sale.save()

            # Ajusta estoque corretamente
            produto.stock += old_quantity - new_quantity
            await produto.save()

            return {
                'status': 200,
                'msg': 'Venda atualizada com sucesso!',
                'sale_id': sale.id,
                'product_id': produto.id,
                'new_total_price': sale.total_price,
                'old_quantity': old_quantity,
                'new_quantity': new_quantity,
                'new_stock': produto.stock,
            }

        else:
            # Deleta venda e devolve quantidade ao estoque
            produto.stock += sale.quantity
            await produto.save()

            await sale.delete()
            return {
                'status': 200,
                'msg': 'Venda deletada com sucesso.',
                'sale_id': sale_id,
                'product_id': produto.id,
                'quantity_returned': sale.quantity,
                'new_stock': produto.stock,
            }

    except Exception as e:
        return {
            'status': 500,
            'error': f'Erro ao atualizar ou deletar venda: {str(e)}',
        }
