import json
from datetime import datetime, time
from zoneinfo import ZoneInfo

from tortoise.functions import Sum
from tortoise.models import Q

from src.core.cache import client
from src.model.sale import Sales


async def sales_of_the_day(user_id: int) -> int:
    """
    sales_of_the_day: Retorna a quantidade de VENDAS (códigos únicos) concluídas no dia atual.
    """

    cache_key = None

    try:

        cache_key = f'sales:{user_id}'
        cache = await client.get(cache_key)

        if cache:
            return json.loads(cache)

        # Data atual e definição de início/fim do dia
        today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
        start_of_day = datetime.combine(
            today, time.min, tzinfo=ZoneInfo('America/Sao_Paulo')
        )
        end_of_day = datetime.combine(
            today, time.max, tzinfo=ZoneInfo('America/Sao_Paulo')
        )

        # 1. Busca todas as vendas do usuário no DIA ATUAL
        sales = await Sales.filter(
            usuario_id=user_id,
            criado_em__gte=start_of_day,  # Filtra por data: maior ou igual ao início do dia
            criado_em__lte=end_of_day,  # Filtra por data: menor ou igual ao fim do dia
        ).all()

        # 2. Extrai os códigos de venda (sale_code)
        # Atenção: Ignoramos vendas com sale_code nulo, se houver
        codes = [
            sale.sale_code for sale in sales if sale.sale_code is not None
        ]

        # 3. Conta a quantidade de códigos de venda ÚNICOS
        sales_quantity = len(set(codes))

        if cache_key:
            await client.setex(
                cache_key, 180, json.dumps(sales_quantity, default=str)
            )

        # Retonando quantidade de vendas
        return sales_quantity

    except Exception as e:
        print(f'Erro em sales_of_the_day: {e}')
        return 0


from tortoise.functions import Sum

# Certifique-se de que a classe Sales, etc., está definida/importada
# ...


async def total_in_sales(user_id: int) -> float:
    """
    Calcula e retorna o valor total de todas as vendas (soma de total_price)
    para um usuário (empresa) específico.
    """
    try:
        from tortoise.functions import Sum

        result = (
            await Sales.filter(usuario_id=user_id)
            .annotate(total_vendas=Sum('total_price'))
            .first()
        )

        if result and hasattr(result, 'total_vendas'):
            return float(result.total_vendas) if result.total_vendas else 0.0
        return 0.0

    except Exception as e:
        print(
            f'Erro ao calcular o total de vendas para o usuário {user_id}: {e}'
        )
        raise
