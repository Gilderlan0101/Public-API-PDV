import importlib
import unittest
from unittest.mock import AsyncMock, patch

# Recarregar o módulo para garantir que os patches funcionem
import src.controllers.caixa.cash_controller

importlib.reload(src.controllers.caixa.cash_controller)
from src.controllers.caixa.cash_controller import CashController


class TestCashControllerDebug(unittest.IsolatedAsyncioTestCase):
    def test_import_paths(self):
        """Teste para verificar se os imports estão corretos"""
        print('=== DEBUG PATHS ===')
        print(f'CashController module: {CashController.__module__}')
        print('===================')

    @patch('src.controllers.caixa.cash_controller.Employees.get_or_none')
    async def test_simple_case(self, mock_employee_get):
        """Teste mais simples para isolar o problema"""
        print('=== TEST SIMPLE CASE ===')

        # ARRANGE - Forma mais segura
        async def mock_employee_coro():
            mock_employee = AsyncMock()
            mock_employee.id = 2
            mock_employee.usuario_id = 1
            return mock_employee

        mock_employee_get.side_effect = mock_employee_coro

        # ACT & ASSERT
        try:
            result = await CashController.abrir_caixa(
                funcionario_id=2,
                saldo_inicial=12.50,
                nome='Maria',
                company_id=1,
            )
            print(f'Result: {result}')
        except Exception as e:
            print(f'Error: {e}')
            raise

    async def test_with_context_manager(self):
        """Teste usando context manager para patches"""
        with patch(
            'src.controllers.caixa.cash_controller.Employees.get_or_none'
        ) as mock_employee_get:
            # Configurar o mock para retornar um AsyncMock
            mock_employee = AsyncMock()
            mock_employee.id = 2
            mock_employee.usuario_id = 1
            mock_employee_get.return_value = mock_employee

            with patch(
                'src.controllers.caixa.cash_controller.Caixa.filter'
            ) as mock_caixa_filter:
                # Configurar chain de métodos
                mock_filter_instance = AsyncMock()
                mock_filter_instance.first.return_value = None
                mock_caixa_filter.return_value = mock_filter_instance

                with patch(
                    'src.controllers.caixa.cash_controller.Caixa.create'
                ) as mock_caixa_create:
                    mock_caixa = AsyncMock()
                    mock_caixa_create.return_value = mock_caixa

                    with patch(
                        'src.controllers.caixa.cash_controller.CashMovement.create'
                    ):
                        # ACT
                        result = await CashController.abrir_caixa(
                            funcionario_id=2,
                            saldo_inicial=12.50,
                            nome='Maria',
                            company_id=1,
                        )

                        # ASSERT
                        self.assertIsNotNone(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
