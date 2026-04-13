import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Configuracao do diretorio raiz para o sys.path
DIR_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DIR_ROOT) not in sys.path:
    sys.path.append(str(DIR_ROOT))

from src.controllers.caixa.cash_controller import CashController


class TestCashControllerDebug(unittest.IsolatedAsyncioTestCase):
    """
    Testes unitarios para o CashController garantindo compatibilidade assincrona.
    """

    @patch(
        'src.controllers.caixa.cash_controller.Employees.get_or_none',
        new_callable=AsyncMock,
    )
    async def test_simple_case(self, mock_employee_get):
        """
        Valida a busca inicial do funcionario com retorno assincrono.
        """
        # Configuracao do mock do funcionario
        mock_employee = MagicMock()
        mock_employee.id = 2
        mock_employee.nome = 'Maria'
        mock_employee_get.return_value = mock_employee

        # Mock para evitar chamadas reais ao banco e tratar o encadeamento assincrono
        with patch(
            'src.controllers.caixa.cash_controller.Caixa.filter'
        ) as mock_filter:
            mock_caixa = AsyncMock()
            mock_caixa.id = 1
            mock_caixa.caixa_id = 'CX-001'

            # Criamos uma chain de mocks onde .filter() retorna o mock e .first() e um AsyncMock
            mock_chain = MagicMock()
            mock_chain.filter.return_value = mock_chain
            mock_chain.first = AsyncMock(side_effect=[mock_caixa, None])
            mock_filter.return_value = mock_chain

            # Patch para a transacao (in_transaction) que agora existe no controller
            with patch(
                'src.controllers.caixa.cash_controller.in_transaction'
            ) as mock_trans:
                mock_trans.return_value.__aenter__ = AsyncMock()
                mock_trans.return_value.__aexit__ = AsyncMock()

                with patch(
                    'src.controllers.caixa.cash_controller.CashMovement.create',
                    new_callable=AsyncMock,
                ):
                    # Execucao do metodo
                    result = await CashController.open_checkout(
                        employe_id=2,
                        initial_balance=12.50,
                        name='Maria',
                        company_id=1,
                    )

                    self.assertIsNotNone(result)

    async def test_with_context_manager(self):
        """
        Simula a cadeia completa de abertura de caixa e persistencia.
        """
        # Patch assincrono para busca de funcionario
        with patch(
            'src.controllers.caixa.cash_controller.Employees.get_or_none',
            new_callable=AsyncMock,
        ) as mock_get_emp:
            emp = MagicMock()
            emp.nome = 'Maria'
            mock_get_emp.return_value = emp

            # Patch do filtro de caixa
            with patch(
                'src.controllers.caixa.cash_controller.Caixa.filter'
            ) as mock_filter:
                caixa_mock = AsyncMock()
                caixa_mock.aberto = False
                caixa_mock.id = 10
                caixa_mock.caixa_id = 'CX-99'

                # Configuracao da chain de filtros: Caixa.filter().first()
                mock_chain = MagicMock()
                mock_chain.filter.return_value = mock_chain
                # O controller chama .first() duas vezes (uma para o caixa, outra para checar se ha aberto)
                mock_chain.first = AsyncMock(side_effect=[caixa_mock, None])
                mock_filter.return_value = mock_chain

                # Patch da transacao do Tortoise ORM (necessario para async with in_transaction)
                with patch(
                    'src.controllers.caixa.cash_controller.in_transaction'
                ) as mock_trans:
                    mock_trans.return_value.__aenter__ = AsyncMock()
                    mock_trans.return_value.__aexit__ = AsyncMock()

                    # Patch para criacao de movimento
                    with patch(
                        'src.controllers.caixa.cash_controller.CashMovement.create',
                        new_callable=AsyncMock,
                    ) as mock_mov:

                        # Execucao
                        result = await CashController.open_checkout(
                            employe_id=2,
                            initial_balance=50.0,
                            name='Caixa Principal',
                            company_id=1,
                        )

                        # Verificacoes de estado
                        self.assertTrue(caixa_mock.aberto)
                        self.assertEqual(caixa_mock.saldo_inicial, 50.0)
                        mock_mov.assert_called_once()
                        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
