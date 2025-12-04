from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist, MultipleObjectsReturned

from src.logs.infos import LOGGER
from src.model.partial import Partial, finished_debts
from src.utils.private_infos import mask_cpf


class ViewsAllDepts:
    def __init__(self, company_id: int, cpf: str = None, user_id: int = None):
        self.company_id = company_id
        self.cpf = cpf
        self.user_id = user_id

    async def get_customer_debt(self):
        """Busca dívidas de um cliente cadastrado nesta empresa."""
        if not isinstance(self.company_id, int):
            LOGGER.info('Ação bloqueada: company_id inválido.')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='ID da empresa inválido',
            )

        try:
            debt_record = await Partial.filter(
                cpf=self.cpf, usuario_id=self.user_id
            ).first()

            if not debt_record:
                LOGGER.warning(f'Dívida não encontrada para CPF: {self.cpf}')
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Nenhuma dívida encontrada para este CPF',
                )

            return debt_record

        except MultipleObjectsReturned:
            LOGGER.error('A busca retornou mais de um objeto.')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro ao processar dívida: múltiplos registros encontrados.',
            )

        except Exception as error:
            LOGGER.error(f'Erro inesperado ao buscar dívida: {str(error)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao buscar dívida',
            )

    async def get_current_debts(self) -> dict:
        """Obtém todas as dívidas em aberto | Pendente de clientes desta empresa."""
        try:
            # ⚠️ CORREÇÃO: Filtrar apenas dívidas com valor > 0
            debts = await Partial.filter(
                usuario_id=self.company_id, value__gt=0
            ).all()  # Apenas dívidas com valor maior que 0

            result = []

            for debt in debts:
                result.append(
                    {
                        'id': debt.id,
                        'customers_name': debt.customers_name,
                        'cpf': debt.cpf,
                        'tel': debt.tel,
                        'product_name': debt.produto,  # ⚠️ Verificar se é 'produto' ou 'product_name'
                        'value': debt.value or 0.0,
                        'payment_method': debt.payment_method,
                        'date': debt.date.isoformat() if debt.date else None,
                    }
                )

            LOGGER.info(
                f'Encontradas {len(result)} dívidas ATIVAS para usuário {self.company_id}'
            )

            return {'status': 200, 'dividas': result, 'total': len(result)}

        except Exception as error:
            LOGGER.error(f'Erro ao buscar dívidas: {str(error)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao buscar dívidas',
            )

    async def get_paid_debts(self) -> dict:
        """Obtém histórico de dívidas quitadas."""
        try:
            paid_debts = await finished_debts.filter(
                usuario_id=self.company_id
            ).all()
            result = []

            for debt in paid_debts:
                result.append(
                    {
                        'id': debt.id,
                        'name': debt.name,
                        'tel': debt.tel,
                        'cpf': debt.cpf,
                        'product_name': debt.product_name,
                        'paid_value': debt.total_paid_value or 0,
                        'original_value': debt.original_debt_value or 0,
                        'payment_history': debt.payment_history or [],
                        'total_payments': len(debt.payment_history or []),
                        'status': debt.status,
                        'date': debt.date.isoformat() if debt.date else None,
                    }
                )

            LOGGER.info(
                f'Encontradas {len(result)} dívidas pagas para usuário {self.company_id}'
            )

            return {
                'status': 200,
                'dividas_pagas': result,
                'total': len(result),
            }

        except Exception as error:
            LOGGER.error(f'Erro ao buscar dívidas pagas: {str(error)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao buscar dívidas pagas',
            )
