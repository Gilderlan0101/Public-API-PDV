from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel
from tortoise.expressions import Q

from src.auth.deps import SystemUser, get_current_user
from src.model.product import Produto
from src.model.sale import Sales

router = APIRouter()


class CancelRequest(BaseModel):
    code: str
    reason: str | None = None


@router.post('/cancel', status_code=status.HTTP_200_OK)
async def cancel_sale(
    body: CancelRequest,
    current_user: SystemUser = Depends(get_current_user),
):
    """Cancela uma venda, restaura estoque e retorna resultado padronizado para frontend"""
    if not current_user.empresa_id:
        return {'success': False, 'data': None, 'error': 'Usuário inválido'}

    try:
        print(f'🔍 Buscando venda com código: {body.code}')
        print(f'👤 Usuário atual ID: {current_user.empresa_id}')

        # 🔹 CORREÇÃO: Buscar a venda pelo sale_code
        sale = await Sales.filter(
            sale_code=body.code.strip(), usuario_id=current_user.empresa_id
        ).first()  # 🔹 CORREÇÃO: campo sale_code existe

        if not sale:
            # 🔹 DEBUG: Listar todas as vendas para ver o que existe
            all_sales = await Sales.filter(
                usuario_id=current_user.empresa_id
            ).all()

            for s in all_sales:
                print(
                    f'  - Venda ID: {s.id}, Sale_code: {s.sale_code}, Produto: {s.product_name}'
                )

            return {
                'success': False,
                'data': None,
                'error': f'Venda não encontrada. Código: {body.code}',
            }

        print(
            f'✅ Venda encontrada: ID {sale.id}, Produto: {sale.product_name}, Sale_code: {sale.sale_code}'
        )

        # 🔹 CORREÇÃO: Buscar o produto pelo relacionamento com a venda
        # Como a venda tem relacionamento com Produto, podemos usar:
        product = await sale.produto

        if not product:
            # Se não encontrou pelo relacionamento, tenta buscar pelo nome do produto
            product = await Produto.filter(
                usuario_id=current_user.empresa_id, name=sale.product_name
            ).first()

        if not product:
            return {
                'success': False,
                'data': None,
                'error': f'Produto não encontrado para a venda {body.code}',
            }

        print(
            f'✅ Produto encontrado: {product.name}, Estoque atual: {product.stock}'
        )

        # 🔹 CORREÇÃO: Restaura o estoque
        quantidade_restaurada = sale.quantity
        product.stock += quantidade_restaurada
        product.atualizado_em = datetime.now(ZoneInfo('America/Sao_Paulo'))
        await product.save()

        print(
            f'📦 Estoque restaurado: +{quantidade_restaurada} unidades. Novo estoque: {product.stock}'
        )

        # 🔹 CORREÇÃO: Marcar a venda como cancelada em vez de deletar
        # (Mantenha o registro para auditoria)
        # Primeiro verifica se o campo existe, se não, apenas deleta
        if hasattr(Sales, 'cancelada'):
            sale.cancelada = True
            sale.motivo_cancelamento = body.reason
            sale.data_cancelamento = datetime.now(
                ZoneInfo('America/Sao_Paulo')
            )
            await sale.save()
            print(f'✅ Venda marcada como cancelada: {sale.id}')
        else:
            # Se não tem campo de cancelamento, deleta a venda
            await sale.delete()
            print(f'✅ Venda deletada: {sale.id}')

        return {
            'success': True,
            'data': {
                'message': 'Venda cancelada com sucesso',
                'sale_code': body.code,
                'product_name': product.name,
                'restored_stock': quantidade_restaurada,
                'new_stock': product.stock,
                'product_id': product.id,
                'sale_id': sale.id,
            },
            'error': None,
        }

    except Exception as e:
        print(f'❌ Erro ao cancelar venda: {str(e)}')
        import traceback

        print(f'📋 Traceback: {traceback.format_exc()}')

        return {
            'success': False,
            'data': None,
            'error': f'Erro inesperado: {str(e)}',
        }
