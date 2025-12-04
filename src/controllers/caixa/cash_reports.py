import json
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from tortoise.expressions import Q

# Cache Redis
from src.core.cache import client
from src.model.caixa import Caixa
from src.model.cashmovement import CashMovement
from src.model.employee import Employees
from src.model.sale import Sales
from src.model.user import Usuario
from src.utils.payments_config import *
from src.utils.status_code import *


class CashReportController:
    async def get_cash_reports(
        self,
        user_id: int,
        filter_data: Optional[datetime] = None,
        employee_name: Optional[str] = None,
    ) -> list[dict]:
        """
        Busca e retorna relatórios de caixa com cache CORRIGIDO.
        """
        # Define a data padrão se nenhuma for fornecida
        current_date_tz = datetime.now(ZoneInfo('America/Sao_Paulo'))

        # 🔹 Chave do cache melhorada
        cache_key = f'cash_reports:{user_id}:{filter_data}:{employee_name}'
        cache = await client.get(cache_key)

        # 🔹 Tenta retornar do cache se a chave existir
        if cache:
            print(f'✅ Retornando dados do cache para a chave: {cache_key}')
            return json.loads(cache)

        current_user = await Usuario.get_or_none(id=user_id)
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Usuário não encontrado.',
            )

        # 🔹 Lógica para filtrar por nome do funcionário
        if employee_name:
            employee_query = await Employees.filter(
                Q(nome__icontains=employee_name)
            ).first()
            if not employee_query:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Funcionário com o nome '{employee_name}' não encontrado.",
                )
            cash_movement_query = CashMovement.filter(
                Q(funcionario_id=employee_query.id) & Q(usuario_id=user_id)
            )
        else:
            cash_movement_query = CashMovement.filter(usuario_id=user_id)

        # 🔹 CORREÇÃO: Filtra pela data fornecida de forma correta
        if filter_data:
            # Converte para date se for datetime
            if isinstance(filter_data, datetime):
                filter_date = filter_data.date()
            else:
                filter_date = filter_data

            # 🔹 CORREÇÃO: Filtro manual por data (Tortoise não suporta __date)
            cash_movements_all = await cash_movement_query.order_by(
                '-criado_em'
            )
            cash_movements = [
                mov
                for mov in cash_movements_all
                if mov.criado_em.date() == filter_date
            ]
        else:
            cash_movements = await cash_movement_query.order_by('-criado_em')

        if not cash_movements:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Nenhum movimento de caixa encontrado com os filtros aplicados.',
            )

        movement_data = []

        # 🔹 CORREÇÃO: Calcular saldo por CAIXA, não acumulado geral
        saldo_por_caixa = {}

        for moviment in cash_movements:
            caixa_id = moviment.caixa_id

            # Inicializa o saldo do caixa se não existir
            if caixa_id not in saldo_por_caixa:
                saldo_por_caixa[caixa_id] = 0.0

            # 🔹 CORREÇÃO: Lógica correta para calcular saldo
            valor = float(moviment.valor)
            if moviment.tipo == 'ENTRADA':
                saldo_por_caixa[caixa_id] += valor
            elif moviment.tipo == 'SAIDA':
                saldo_por_caixa[caixa_id] -= valor
            # ABERTURA geralmente é o saldo inicial, não soma

            # 🔹 CORREÇÃO: Mostrar informações claras
            movement_data.append(
                {
                    'data_hora': moviment.criado_em.strftime('%d/%m/%Y %H:%M'),
                    'tipo_movimento': moviment.tipo,
                    'valor': valor,
                    'caixa_id': caixa_id,
                    'funcionario_id': moviment.funcionario_id,
                    'saldo_caixa_atual': saldo_por_caixa[
                        caixa_id
                    ],  # Saldo deste caixa específico
                    'descricao': moviment.descricao
                    if hasattr(moviment, 'descricao')
                    else 'Movimento de caixa',
                }
            )

        # 🔹 CORREÇÃO: Ordenar por data mais recente primeiro
        movement_data.sort(key=lambda x: x['data_hora'], reverse=True)

        await client.setex(
            cache_key, 300, json.dumps(movement_data)
        )  # 5 minutos de cache
        return movement_data

    async def get_cash_summary(
        self, user_id: int, filter_data: Optional[datetime] = None
    ) -> dict:
        """
        Retorna um resumo consolidado dos caixas.
        """
        movements = await self.get_cash_reports(user_id, filter_data)

        # 🔹 Calcular totais
        total_entradas = sum(
            m['valor'] for m in movements if m['tipo_movimento'] == 'ENTRADA'
        )
        total_saidas = sum(
            m['valor'] for m in movements if m['tipo_movimento'] == 'SAIDA'
        )
        saldo_total = total_entradas - total_saidas

        # 🔹 Agrupar por caixa
        caixas = {}
        for mov in movements:
            caixa_id = mov['caixa_id']
            if caixa_id not in caixas:
                caixas[caixa_id] = {'entradas': 0, 'saidas': 0, 'saldo': 0}

            if mov['tipo_movimento'] == 'ENTRADA':
                caixas[caixa_id]['entradas'] += mov['valor']
            elif mov['tipo_movimento'] == 'SAIDA':
                caixas[caixa_id]['saidas'] += mov['valor']

            caixas[caixa_id]['saldo'] = (
                caixas[caixa_id]['entradas'] - caixas[caixa_id]['saidas']
            )

        return {
            'resumo': {
                'total_entradas': total_entradas,
                'total_saidas': total_saidas,
                'saldo_total': saldo_total,
                'quantidade_movimentos': len(movements),
                'quantidade_caixas': len(caixas),
            },
            'caixas': caixas,
            'movimentos': movements,
        }
