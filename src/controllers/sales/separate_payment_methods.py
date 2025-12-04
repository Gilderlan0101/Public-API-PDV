import json
from datetime import datetime
from typing import Any, Dict, List

from fastapi import HTTPException, status

from src.core.cache import client
from src.model.sale import Sales


async def separating_sales_by_payments(
    user_id: int,
) -> Dict[str, Dict[str, Any]]:
    """
    Separa todas as vendas por métodos de pagamentos, calculando o valor total
    (em Reais) e a quantidade total de itens para cada método.

    Retorna um dicionário onde a chave é o método de pagamento e o valor
    contém os totais e a lista detalhada de vendas.
    """

    # 🎯 ESTRUTURA CORRIGIDA: Inicializa os métodos com os contadores zerados
    methods: Dict[str, Dict[str, Any]] = {
        'PIX': {'total_value': 0.0, 'total_quantity': 0, 'sales_list': []},
        'CARTAO': {'total_value': 0.0, 'total_quantity': 0, 'sales_list': []},
        'DINHEIRO': {
            'total_value': 0.0,
            'total_quantity': 0,
            'sales_list': [],
        },
        'NOTA': {'total_value': 0.0, 'total_quantity': 0, 'sales_list': []},
        'FIADO': {'total_value': 0.0, 'total_quantity': 0, 'sales_list': []},
    }

    try:
        cache_key = f'payments:{user_id}'
        cache = await client.get(cache_key)

        if cache:
            return json.loads(cache)

        if not user_id:
            return methods

        all_sales = await Sales.filter(usuario_id=user_id)

        for prod in all_sales:
            # Garante que o método de pagamento seja sempre em UPPERCASE,
            # para corresponder às chaves do nosso dicionário 'methods'
            payment_key = prod.payment_method.upper()

            # Monta o objeto de dados detalhado da venda
            data = {
                'id': prod.id,
                'Product_name': prod.product_name,
                'amount': prod.quantity,
                'price': prod.total_price,
                # Ajuste no formato da data para incluir a hora correta da venda
                'date': prod.criado_em.strftime('%d/%m/%Y %H:%M:%S'),
            }

            # ATUALIZAÇÃO DOS TOTAIS E ADIÇÃO DA VENDA DETALHADA
            if payment_key in methods:
                # 1. Adiciona os dados detalhados à lista
                methods[payment_key]['sales_list'].append(data)

                # 2. Atualiza o valor total vendido
                methods[payment_key]['total_value'] += prod.total_price

                # 3. Atualiza a quantidade total de itens vendidos
                methods[payment_key]['total_quantity'] += prod.quantity

            # Nota: O 'else' original que criava uma nova chave não é mais necessário,
            # pois PaymentMethods garante que as chaves já existem.
            # Se for necessário tratar métodos de pagamento não mapeados, adicione o 'else' aqui.

        # 🔹 Antes de salvar, convertemos os números de ponto flutuante para strings formatadas
        # (Opcional, mas ajuda a manter o formato monetário na saída final)
        final_result = {}
        for key, value in methods.items():
            final_result[key] = {
                'total_value': f"R$ {value['total_value']:.2f}",
                'total_quantity': value['total_quantity'],
                'sales_list': value['sales_list'],
            }

        await client.setex(
            cache_key, 60, json.dumps(final_result, default=str)
        )
        return final_result

    except Exception as e:
        # É importante registrar o erro (e) em um log de produção
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro desconhecido: {e}',
        )
