# import json
# from datetime import datetime
# from fastapi import HTTPException
# from src.core.cache import client
# from src.model.sale import Sales


# async def information_about_sales_and_products_and_employees(user_id: int) -> list[dict]:
#     """
#     Função responsável por listar todos os produtos vinculados às vendas de um usuário específico.

#     Essa função busca as vendas associadas ao `user_id` informado,
#     trazendo informações detalhadas da venda, do produto relacionado
#     e do caixa (se existir). Para otimizar o desempenho, os dados
#     são armazenados em cache.

#     Parameters
#     ----------
#     user_id : int
#         ID do usuário que será utilizado para filtrar as vendas.

#     Returns
#     -------
#     list[dict] or None
#         Retorna uma lista de dicionários contendo informações de vendas,
#         produtos e caixa. Caso `user_id` não seja informado ou não existam
#         registros, retorna `None`.
#     """

#     if not user_id:
#         return None

#     # 🔹 Gerando chave de cache
#     cache_key = f"product_utils:{user_id}"
#     cache = client.get(cache_key)

#     if cache:
#         return json.loads(cache)

#     products: list[dict] = []

#     try:
#         # 🔹 Busca todas as vendas do usuário com seus produtos relacionados
#         query_product = await Sales.filter(usuario_id=user_id).prefetch_related("produto", "caixa", "funcionario")


#         if not query_product:
#             return None

#         for return_products in query_product:
#             # Converte datetime para string ISO 8601
#             created_in_str = return_products.criado_em.isoformat() if return_products.criado_em else None

#             products.append(
#                 {
#                     "sales": {
#                         "id": return_products.id,
#                         "quantity": return_products.quantity,
#                         "total_price": return_products.total_price,
#                         "total_profit": return_products.lucro_total,
#                         "cost_price": return_products.cost_price,
#                         "sale_code": return_products.sale_code,
#                         "payment_method": return_products.payment_method,
#                         "created_in": created_in_str,
#                         "employee": (return_products.funcionario.id if return_products.funcionario else None),
#                     },
#                     "products": {
#                         "name": return_products.product_name,
#                         "lot_bar_code": return_products.produto.lot_bar_code,
#                         "image_url": return_products.produto.image_url or None,
#                         "ticket": return_products.produto.ticket or None,
#                         "sale_price": return_products.produto.sale_price,
#                     },
#                     "caixa": {
#                         "id": return_products.caixa.id if return_products.caixa else None,
#                         "name": return_products.caixa.nome if return_products.caixa else None,
#                         "valor_fechamento": (return_products.caixa.valor_fechamento if return_products.caixa  else "Não definido ainda."),
#                         "valor_total": (return_products.caixa.valor_total if return_products.caixa else "Não definido ainda."),
#                         "change": (return_products.caixa.change if return_products.caixa else None),
#                     },
#                 }
#             )

#         # 🔹 Armazenando no cache por 60s
#         client.setex(cache_key, 60, json.dumps(products, default=str))
#         return products

#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Erro interno [ information_about_sales_and_products_and_employees ]: {e}"
#         )
#         return None
