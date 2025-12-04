from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist

from src.logs.infos import LOGGER
from src.model.partial import Partial, finished_debts


class Person:
    """
    Classe responsável por criar cliente antes de venda no modo parcial
    """

    def __init__(self, full_name: str, cpf: str, tel: str, user_id: int):
        self.full_name = full_name
        self.cpf = self._clean_cpf(cpf)
        self.tel = self._clean_phone(tel)
        self.user_id = user_id

    def _clean_cpf(self, cpf: str) -> str:
        """Remove caracteres especiais do CPF"""
        return cpf.replace('.', '').replace('-', '')

    def _clean_phone(self, tel: str) -> str:
        """Remove caracteres especiais do telefone"""
        return (
            tel.replace('(', '')
            .replace(')', '')
            .replace(' ', '')
            .replace('-', '')
        )

    async def create_customer(self) -> bool:
        """
        Cria cliente se não existir
        Retorna True se criou, False se já existe
        """
        try:
            existing_customer = await Partial.filter(
                cpf=self.cpf, usuario_id=self.user_id
            ).first()

            if not existing_customer:
                await Partial.create(
                    usuario_id=self.user_id,
                    customers_name=self.full_name,
                    cpf=self.cpf,
                    tel=self.tel,
                    produto='',  # Produto será definido na venda
                    value=0.0,
                    payment_method=None,
                )
                LOGGER.info(f'Cliente {self.full_name} criado com sucesso')
                return True

            LOGGER.info(f'Cliente {self.full_name} já existe')
            return False

        except Exception as error:
            LOGGER.error(f'Erro ao criar cliente: {str(error)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao criar cliente',
            )

    async def _calculate_new_balance(self, debt_record: Partial) -> tuple:
        """Calcula novo saldo após pagamento"""
        try:
            current_balance = Decimal(str(debt_record.value or '0'))
            paid_value = Decimal(str(self.value_received))

            LOGGER.info(
                f'Saldo atual: {current_balance}, Pagamento: {paid_value}'
            )

            if paid_value > current_balance:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'Pagamento maior que dívida: R$ {paid_value} > R$ {current_balance}',
                )

            remaining_balance = float(current_balance) - float(paid_value)
            return current_balance, remaining_balance

        except (InvalidOperation, ValueError) as error:
            LOGGER.error(f'Erro no cálculo do saldo: {str(error)}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Erro no cálculo do saldo',
            )
