from datetime import datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from tortoise.exceptions import DoesNotExist

from src.logs.infos import LOGGER
from src.model.partial import Partial, finished_debts
from src.utils.private_infos import mask_cpf


class PartialPayment:
    """
    Classe para processar pagamentos parciais de dívidas
    """

    def __init__(
        self,
        payment_method: str,
        value_received: float,
        cpf: str,
        user_id: int,
    ):
        self.payment_method = payment_method.upper()
        self.value_received = value_received
        self.cpf = self._clean_cpf(cpf)
        self.user_id = user_id

    def _clean_cpf(self, cpf: str) -> str:
        """Remove caracteres especiais do CPF"""
        return cpf.replace('.', '').replace('-', '')

    def _validate_input_data(self) -> None:
        """Valida dados de entrada do pagamento"""
        if not self.cpf or len(self.cpf) != 11:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='CPF deve conter 11 dígitos',
            )

        if self.value_received is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Valor recebido é obrigatório',
            )

        try:
            paid_value = Decimal(str(self.value_received))
            if paid_value <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Valor recebido deve ser maior que zero',
                )
        except (InvalidOperation, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Valor recebido inválido',
            )

    async def _get_debt_record(self) -> Partial:
        """Busca o registro específico da dívida pelo CPF"""
        try:
            debt_record = await Partial.filter(
                usuario_id=self.user_id, cpf=self.cpf
            ).first()

            if not debt_record:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Nenhuma dívida encontrada para este CPF',
                )

            return debt_record

        except Exception as error:
            LOGGER.error(f'Erro ao buscar dívida específica: {str(error)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao buscar dívida',
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

    async def _register_payment_history(
        self,
        debt_record: Partial,
        current_balance: Decimal,
        remaining_balance: float,
    ):
        """Registra o pagamento no histórico"""
        try:
            payment_history = {
                'date': datetime.now(
                    ZoneInfo('America/Sao_Paulo')
                ).isoformat(),
                'amount': float(self.value_received),
                'method': self.payment_method,
                'previous_balance': float(current_balance),
                'new_balance': remaining_balance,
            }

            # Atualizar histórico de pagamentos se existir
            if (
                hasattr(debt_record, 'payment_history')
                and debt_record.payment_history
            ):
                history = debt_record.payment_history
                if isinstance(history, list):
                    history.append(payment_history)
                else:
                    history = [payment_history]
            else:
                history = [payment_history]

            await Partial.filter(id=debt_record.id).update(
                payment_history=history
            )

        except Exception as error:
            LOGGER.error(f'Erro ao registrar histórico: {str(error)}')
            # Não interrompe o fluxo principal se houver erro no histórico

    async def _update_or_remove_debt(
        self,
        debt_record: Partial,
        remaining_balance: float,
        current_balance: Decimal,
    ) -> dict:
        try:
            if remaining_balance <= 0:
                # Dívida quitada - mover para histórico e remover
                await self._move_to_paid_debts(debt_record, current_balance)

                return {
                    'status': 'quitada',
                    'message': 'Dívida quitada com sucesso!',
                    'troco': abs(remaining_balance)
                    if remaining_balance < 0
                    else 0,
                    'valor_pago': float(self.value_received),
                    'valor_original': float(current_balance),
                }
            else:
                # ⚠️ CORREÇÃO: Garantir que o valor seja atualizado mesmo quando for 0
                new_value = remaining_balance if remaining_balance > 0 else 0

                await Partial.filter(id=debt_record.id).update(
                    value=new_value,
                    payment_method=self.payment_method,  # Garantir que seja 0 se remaining_balance for <= 0
                )

            # Buscar registro atualizado
            updated_record = await Partial.filter(id=debt_record.id).first()

            return {
                'status': 'parcial',
                'message': 'Pagamento parcial registrado!',
                'saldo_restante': new_value,
                'valor_pago': float(self.value_received),
                'valor_original': float(current_balance),
                'cliente': updated_record.customers_name
                if updated_record
                else debt_record.customers_name,
            }

        except Exception as error:
            LOGGER.error(f'Erro ao atualizar/remover dívida: {str(error)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro ao processar pagamento',
            )

    async def _move_to_paid_debts(
        self, debt_record: Partial, original_balance: Decimal
    ):
        """Move dívida quitada para a tabela de dívidas pagas"""
        try:
            # Criar registro em finished_debts
            await finished_debts.create(
                usuario_id=self.user_id,
                name=debt_record.customers_name,
                cpf=debt_record.cpf,
                tel=debt_record.tel,
                product_name=debt_record.produto,
                total_paid_value=float(self.value_received),
                original_debt_value=float(original_balance),
                payment_method=self.payment_method,
                status='quitada',
                date=datetime.now(ZoneInfo('America/Sao_Paulo')),
            )

            # Remover da tabela de dívidas ativas
            await debt_record.delete()

        except Exception as error:
            LOGGER.error(f'Erro ao mover dívida para pagas: {str(error)}')
            raise

    async def update_value(self) -> dict:
        """
        Processa pagamento parcial de uma dívida

        Fluxo:
        1. Valida dados de entrada
        2. Busca dívida específica do cliente
        3. Calcula novo saldo
        4. Registra pagamento no histórico
        5. Atualiza ou remove dívida
        6. Retorna resultado
        """

        # Validação inicial dos dados
        self._validate_input_data()

        # Busca dívida específica do cliente (objeto Partial, não dicionário)
        debt_record = await self._get_debt_record()

        # Calcula novo saldo após pagamento
        current_balance, remaining_balance = await self._calculate_new_balance(
            debt_record
        )

        # Registra pagamento no histórico
        await self._register_payment_history(
            debt_record, current_balance, remaining_balance
        )

        # Atualiza ou remove dívida conforme saldo
        result = await self._update_or_remove_debt(
            debt_record, remaining_balance, current_balance
        )

        return result

    # Mantém o método original para outras finalidades
    async def get_current_debts(self) -> dict:
        """Obtém todas as dívidas em aberto | Pendente de clientes desta empresa."""
        try:
            debts = await Partial.filter(usuario_id=self.user_id).all()
            result = []

            for debt in debts:
                result.append(
                    {
                        'id': debt.id,
                        'customers_name': debt.customers_name,
                        'cpf': debt.cpf,
                        'tel': debt.tel,
                        'product_name': debt.produto,
                        'value': debt.value or 0.0,
                        'payment_method': debt.payment_method,
                        'date': debt.date.isoformat() if debt.date else None,
                    }
                )

            LOGGER.info(
                f'Encontradas {len(result)} dívidas para usuário {self.user_id}'
            )

            return {'status': 200, 'dividas': result, 'total': len(result)}

        except Exception as error:
            LOGGER.error(
                f'Erro ao buscar dívidas [ PROCESS_PARTIAL_PAYMENTS (get_current_debts) ] : {str(error)}'
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao buscar dívidas',
            )
