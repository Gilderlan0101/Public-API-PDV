from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist

from src.logs.infos import LOGGER
from src.model.partial import Partial, finished_debts


class UpdateDepts:
    def __init__(self):
        pass

    async def _register_payment_history(
        self,
        debt_record: Partial,
        current_balance: Decimal,
        remaining_balance: float,
    ) -> None:
        """Registra pagamento no histórico de dívidas quitadas"""
        try:
            payment_data = {
                'date': datetime.now(
                    ZoneInfo('America/Sao_Paulo')
                ).isoformat(),
                'payment_method': self.payment_method,
                'paid_value': float(self.value_received),
                'previous_balance': float(current_balance),
                'new_balance': remaining_balance,
            }

            # 🔥 MUDANÇA CRÍTICA: Verifica se já existe registro para este CPF
            existing_finished_debt = await finished_debts.filter(
                cpf=debt_record.cpf,
                usuario_id=self.user_id,
                product_name=debt_record.produto,
            ).first()

            if existing_finished_debt:
                # 🔥 ATUALIZA registro existente
                payment_history = existing_finished_debt.payment_history or []
                payment_history.append(payment_data)

                # Atualiza totais
                existing_finished_debt.total_paid_value += float(
                    self.value_received
                )
                existing_finished_debt.payment_history = payment_history

                # Se a dívida foi quitada, atualiza status
                if remaining_balance <= 0:
                    existing_finished_debt.status = 'quitada'

                await existing_finished_debt.save()
                LOGGER.info(
                    f'Pagamento adicionado ao histórico existente para {debt_record.customers_name}'
                )

            else:
                # 🔥 CRIA novo registro apenas se não existir
                await finished_debts.create(
                    name=debt_record.customers_name,
                    product_name=debt_record.produto,
                    cpf=debt_record.cpf,
                    tel=debt_record.tel,
                    original_debt_value=float(current_balance)
                    + float(self.value_received),  # Valor original total
                    total_paid_value=float(self.value_received),
                    payment_history=[
                        payment_data
                    ],  # Array com primeiro pagamento
                    status='parcial' if remaining_balance > 0 else 'quitada',
                    usuario_id=self.user_id,
                )
                LOGGER.info(
                    f'Novo histórico criado para {debt_record.customers_name}'
                )

        except Exception as error:
            LOGGER.error(
                f'Erro ao registrar pagamento no histórico: {str(error)}'
            )
            # Não interrompe fluxo principal se falhar registro histórico

    async def _update_or_remove_debt(
        self,
        debt_record: Partial,
        remaining_balance: float,
        current_balance: Decimal,
    ) -> dict:
        """Atualiza ou remove dívida conforme saldo restante"""
        try:
            if remaining_balance <= 0:
                # Dívida totalmente quitada
                change = abs(remaining_balance)
                await debt_record.delete()

                LOGGER.info(f'Dívida quitada para CPF: {self.cpf}')

                return {
                    'message': 'Dívida quitada com sucesso',
                    'cpf': self.cpf,
                    'novo_valor': 0.0,
                    'change': change,
                    'status': 'quitada',
                }
            else:
                # Atualiza saldo da dívida
                debt_record.value = float(remaining_balance)
                debt_record.payment_method = self.payment_method
                debt_record.date = datetime.now(ZoneInfo('America/Sao_Paulo'))
                await debt_record.save()

                LOGGER.info(
                    f'Pagamento parcial registrado para CPF: {self.cpf}'
                )

                return {
                    'message': 'Pagamento parcial registrado',
                    'cpf': self.cpf,
                    'novo_valor': float(remaining_balance),
                    'ultimo_pagamento': float(self.value_received),
                    'status': 'pendente',
                }

        except Exception as error:
            LOGGER.error(f'Erro ao atualizar dívida: {str(error)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao atualizar dívida',
            )

    @staticmethod
    def _calculate_total_paid(debt) -> float:
        """Calcula valor total pago a partir dos pagamentos"""
        total_paid = 0.0

        if debt.payments and isinstance(debt.payments, dict):
            if 'paid_value' in debt.payments:
                total_paid += float(debt.payments.get('paid_value', 0))
            # Adicione mais lógica se houver estrutura complexa de pagamentos

        return total_paid if total_paid > 0 else (debt.value or 0)
