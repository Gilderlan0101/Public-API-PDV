import json
from datetime import datetime
from typing import Any, Dict, List

from fastapi import HTTPException, status

from src.core.cache import client
from src.model.sale import Sales


async def information_about_sales_and_products_and_employees(
    user_id: int,
) -> Dict[str, List[Dict[str, Any]]] | None:
    """
    Função responsável por listar todos os produtos vinculados às vendas de um usuário específico,
    agrupando os resultados pelo ID do Caixa (Ponto de Venda).

    Essa função busca as vendas associadas ao `user_id` informado,
    trazendo informações detalhadas da venda, do produto relacionado
    e do caixa (se existir). Para otimizar o desempenho, os dados
    são armazenados em cache.

    Parameters
    ----------
    user_id : int
        ID do usuário que será utilizado para filtrar as vendas.

    Returns
    -------
    Dict[str, List[Dict[str, Any]]] or None
        Retorna um dicionário onde a chave é o ID do Caixa (string) e o valor
        é uma lista de dicionários contendo informações detalhadas de vendas,
        produtos e caixa. Retorna None se o user_id for inválido ou não houver vendas.
    """

    if not user_id:
        return None

    # 🔹 Gerando chave de cache
    cache_key = f'product_utils:{user_id}'
    cache = await client.get(cache_key)

    if cache:
        return json.loads(cache)

    # 🎯 Inicializando 'sales_by_caixa' como um dicionário para agrupar as vendas
    sales_by_caixa: Dict[str, List[Dict[str, Any]]] = {}

    try:
        # 🔹 Busca todas as vendas do usuário com seus produtos relacionados
        query_product = await Sales.filter(
            usuario_id=user_id
        ).prefetch_related('produto', 'caixa', 'funcionario')

        if not query_product:
            return None

        for return_products in query_product:
            # Converte datetime para string ISO 8601
            created_in_str = (
                return_products.criado_em.isoformat()
                if return_products.criado_em
                else None
            )

            # Determinar a chave de agrupamento (Caixa ID ou "SEM_CAIXA")
            # Usamos str(id) para garantir que a chave do dicionário seja string.
            caixa_id = (
                str(return_products.caixa.id)
                if return_products.caixa
                else 'SEM_CAIXA'
            )

            # 3. Montar o objeto de dados da venda
            sale_data = {
                'sales': {
                    'id': return_products.id,
                    'quantity': return_products.quantity,
                    'total_price': return_products.total_price,
                    'total_profit': return_products.lucro_total,
                    'cost_price': return_products.cost_price,
                    'sale_code': return_products.sale_code,
                    'payment_method': return_products.payment_method,
                    'created_in': created_in_str,
                    'employee': (
                        return_products.funcionario.nome
                        if return_products.funcionario
                        else 'Não foi possível localizar nome do funcionário.'
                    ),
                },
                'products': {
                    'name': return_products.produto.name,  # Assumindo que o campo é 'name' e não 'product_name'
                    'lot_bar_code': (
                        return_products.produto.lot_bar_code
                        if return_products.produto
                        and return_products.produto.lot_bar_code is not None
                        else 'Sem código de barras (cuidado).'
                    ),
                    'image_url': return_products.produto.image_url or None,
                    'ticket': return_products.produto.ticket or None,
                    'sale_price': return_products.produto.sale_price,
                },
                'caixa': {
                    'id': return_products.caixa.id
                    if return_products.caixa
                    else None,
                    'name': return_products.caixa.nome
                    if return_products.caixa
                    else None,
                    'valor_fechamento': (
                        return_products.caixa.valor_fechamento
                        if return_products.caixa
                        and return_products.caixa.valor_fechamento is not None
                        else 'Não definido ainda.'
                    ),
                    'saldo_atual': (
                        return_products.caixa.saldo_atual
                        if return_products.caixa
                        else 'Não definido ainda.'
                    ),
                    'change': (
                        return_products.caixa.change
                        if return_products.caixa
                        and return_products.caixa.change
                        else 'Sem troco'
                    ),
                },
            }

            # Agrupar a venda na lista do caixa correspondente
            if caixa_id not in sales_by_caixa:
                sales_by_caixa[caixa_id] = []

            sales_by_caixa[caixa_id].append(sale_data)

        # 🔹 Armazenando no cache por 60s
        await client.setex(
            cache_key, 60, json.dumps(sales_by_caixa, default=str)
        )

        return sales_by_caixa

    except Exception as e:
        # Logar o erro 'e' para fins de debug é essencial em ambientes de produção
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno ao processar vendas: {e}',
        )
