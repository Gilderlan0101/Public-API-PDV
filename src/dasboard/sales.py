from datetime import datetime, time
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from tortoise.functions import Sum

from src.model.sale import Sales
from src.utils.format_data import format_currency
from src.utils.sales_of_the_day import sales_of_the_day, total_in_sales


def specific_date():
    """Definição de datas"""
    today = datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    start_of_day = datetime.combine(
        today, time.min, tzinfo=ZoneInfo('America/Sao_Paulo')
    )
    end_of_day = datetime.combine(
        today, time.max, tzinfo=ZoneInfo('America/Sao_Paulo')
    )

    return {
        'today': today,
        'start_of_day': start_of_day,
        'end_of_day': end_of_day,
    }


async def query_of_all_sales(company_id: int):
    """
    Consultar todas as vendas desta empresa.
    Busca todas as vendas da empresa no dia atual.
    Consulta de agregação (para todo itens vendidos)
    """
    temp = specific_date()

    try:
        # Busca vendas todas as vendas da empresa
        sales_of_day_list = await Sales.filter(
            usuario_id=company_id,
            criado_em__range=[
                temp.get('start_of_day'),
                temp.get('end_of_day'),
            ],
        ).all()

        # Busca com agregação (total de itens vendidos do dia)
        daily_aggregation = (
            await Sales.filter(
                usuario_id=company_id,
                criado_em__range=[
                    temp.get('start_of_day'),
                    temp.get('end_of_day'),
                ],
            )
            .annotate(total_items_sold=Sum('quantity'))
            .first()
        )

        # Contagem de vendas
        quantity_sales_today = await sales_of_the_day(company_id)
        __value__no__update = await total_in_sales(company_id)
        total_sales_count = await Sales.filter(usuario_id=company_id).count()

    except Exception as e:
        print(f'Erro no primeiro try: {e}')
        return {}

    try:
        # Processamento de dados
        total_user_profit = 0.0
        Total_net_profit_for_the_day = 0.0
        sales_list: List[Dict] = []

        for sale in sales_of_day_list:
            # Simplifique a conversão
            total_user_profit += float(sale.total_price)
            Total_net_profit_for_the_day += float(sale.lucro_total)

            sales_list.append(
                {
                    'id': sale.id,
                    'product_name': sale.product_name,
                    'quantity': sale.quantity,
                    'total_price': format_currency(value=sale.total_price),
                    'lucro_total': format_currency(value=sale.lucro_total),
                    'const_price': format_currency(value=sale.cost_price),
                    'sales_code': sale.sale_code,
                    'payment_method': sale.payment_method,
                    'created_at': sale.criado_em.strftime('%d/%m/%Y %H:%M:%S')
                    if sale.criado_em
                    else None,
                }
            )

        # Total de itens vendidos hoje (FORA do loop)
        total_items_sold_today = (
            daily_aggregation.total_items_sold
            if daily_aggregation and daily_aggregation.total_items_sold is not None
            else 0
        )

        return {
            'total_user_profit': format_currency(value=total_user_profit),
            'total_lucro': format_currency(value=__value__no__update),
            'sales_of_the_day': quantity_sales_today,
            'total_items_sold_today': total_items_sold_today,
            'total_sales_count_history': total_sales_count,
            'sales': sales_list,
        }

    except Exception as e:
        print(f'Erro no segundo try: {e}')
        return {}
