# from typing import Dict, Any
# from src.model.caixa import Caixa
# from src.model.sale import Sales


# async def get_caixa_details(caixa_id: int) -> Dict[str, Any]:
#     """
#     Retorna o resumo do caixa para fechamento automático:
#     - Lista de vendas associadas a este caixa
#     - Total por tipo de pagamento
#     - Valor total das vendas (valor_sistema)
#     """
#     # Busca o caixa
#     caixa = await Caixa.get_or_none(id=caixa_id)
#     if not caixa:
#         raise ValueError("Caixa não encontrado.")

#     # Busca todas as vendas deste caixa específico
#     vendas = await Sales.filter(caixa_id=caixa_id).all()

#     # Inicializa totais
#     total_sistema = 0.0
#     total_por_pagamento: Dict[str, float] = {}

#     for venda in vendas:
#         total_sistema += venda.total_price
#         tipo_pagamento = getattr(venda, "payment_method", "PIX")
#         total_por_pagamento[tipo_pagamento] = total_por_pagamento.get(tipo_pagamento, 0) + venda.total_price

#     return {
#         "caixa_id": caixa.id,
#         "funcionario_id": caixa.nome,
#         "valor_abertura": caixa.saldo_inicial,
#         "valor_sistema": total_sistema,
#         "total_por_pagamento": total_por_pagamento,
#         "total_vendas": len(vendas),
#         "vendas": vendas,
#     }
