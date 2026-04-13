import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Tuple

from fastapi import HTTPException, status
from src.logs.infos import LOGGER
from src.model.partial import Partial


class Person:
    """
    Gerencia a identificacao e persistencia de clientes para operacoes
    de pagamento parcial (venda a prazo/fiado).
    """

    def __init__(self, full_name: str, cpf: str, tel: str, user_id: int):
        self.full_name = full_name.strip()
        self.cpf = self._clean_cpf(cpf)
        self.tel = self._clean_phone(tel)
        self.user_id = user_id
        # Atributo esperado por metodos internos de calculo
        self.value_received = 0.0

    def _sanitize_digits(self, value: str) -> str:
        """Remove qualquer caractere que nao seja um digito."""
        return re.sub(r'\D', '', value) if value else ''

    def _clean_cpf(self, cpf: str) -> str:
        """Higieniza o CPF removendo pontos e hifens."""
        return self._sanitize_digits(cpf)

    def _clean_phone(self, tel: str) -> str:
        """Higieniza o telefone removendo mascaras e espacos."""
        return self._sanitize_digits(tel)

    async def create_customer(self) -> bool:
        """
        Verifica a existencia e realiza o cadastro do cliente na base de dados parcial.
        Retorna True para novo cadastro e False caso o cliente ja exista.
        """
        try:
            # Busca otimizada por CPF e vinculo com a empresa (user_id)
            existing_customer = await Partial.filter(
                cpf=self.cpf, usuario_id=self.user_id
            ).first()

            if existing_customer:
                LOGGER.info(
                    f'Cliente ja cadastrado: {self.full_name} (CPF: {self.cpf})'
                )
                return False

            # Criacao do registro inicial de debito/parcial
            await Partial.create(
                usuario_id=self.user_id,
                customers_name=self.full_name,
                cpf=self.cpf,
                tel=self.tel,
                produto='',  # Placeholder: sera preenchido no ato da venda
                value=0.0,
                payment_method=None,
            )

            LOGGER.info(f'Novo cliente parcial registrado: {self.full_name}')
            return True

        except Exception as error:
            LOGGER.error(
                f'Falha critica na criacao do cliente {self.full_name}: {error}'
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao processar cadastro do cliente.',
            )

    async def _calculate_new_balance(
        self, debt_record: Partial
    ) -> Tuple[Decimal, float]:
        """
        Calcula a amortizacao da divida com precisao decimal.
        Retorna uma tupla contendo (saldo_atual_decimal, novo_saldo_float).
        """
        try:
            # Conversao para Decimal para evitar erros de precisao em ponto flutuante
            current_balance = Decimal(str(debt_record.value or '0'))
            paid_value = Decimal(str(self.value_received))

            if paid_value > current_balance:
                LOGGER.warning(
                    f'Tentativa de pagamento excedente: Div {current_balance} | Pgto {paid_value}'
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'O valor do pagamento (R$ {paid_value}) excede o total da divida (R$ {current_balance}).',
                )

            # Calculo do saldo remanescente
            remaining_balance = float(current_balance - paid_value)

            LOGGER.info(
                f'Calculo de amortizacao concluido para CPF {self.cpf}'
            )
            return current_balance, remaining_balance

        except (InvalidOperation, ValueError) as error:
            LOGGER.error(f'Erro de processamento numerico: {error}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Valores numericos invalidos para processamento financeiro.',
            )
