import sys
import unittest
from dataclasses import is_dataclass
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

# Configuracao do diretorio raiz para o sys.path
DIR_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DIR_ROOT) not in sys.path:
    sys.path.append(str(DIR_ROOT))

from src.controllers.sales.sales import Checkout


class TestCheckout(unittest.IsolatedAsyncioTestCase):
    """
    Suite de testes para validar o fluxo de checkout e processamento de vendas.
    Garante a integridade do sistema em execucao local.
    """

    def test_if_it_is_a_dataclass(self):
        """Verifica se a classe Checkout mantem a estrutura de dataclass."""
        self.assertTrue(is_dataclass(Checkout))

    @patch(
        'src.controllers.sales.sales.VALID_PAYMENT_METHODS',
        ['PIX', 'CARTAO', 'DINHEIRO'],
    )
    def test_constructor_and_payment_validation(self):
        """Valida a inicializacao e a restricao de metodos de pagamento."""
        checkout = Checkout(
            user_id=1,
            product_name='Coca-Cola 2L',
            quantity=10,
            payment_method='PIX',
        )
        self.assertEqual(checkout.payment_method, 'PIX')

        with self.assertRaises(ValueError):
            Checkout(payment_method='METODO_INEXISTENTE')

    @patch('src.controllers.sales.sales.Produto.filter')
    async def test_get_product_by_user_success(self, mock_produto_filter):
        """Valida a busca de produto via ORM."""
        mock_product = MagicMock()
        mock_product.name = 'Produto Teste'

        mock_chain = MagicMock()
        mock_chain.filter.return_value = mock_chain
        mock_chain.first = AsyncMock(return_value=mock_product)
        mock_produto_filter.return_value = mock_chain

        checkout = Checkout()
        result = await checkout.get_product_by_user(user_id=1, code='ABC')

        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'Produto Teste')

    @patch('src.controllers.sales.sales.Employees.filter')
    async def test_resolve_operator_as_admin(self, mock_emp_filter):
        """Verifica se o sistema identifica o admin como operador."""
        mock_chain = MagicMock()
        mock_chain.first = AsyncMock(return_value=None)
        mock_emp_filter.return_value = mock_chain

        current_user = MagicMock()
        current_user.id = 1
        current_user.username = 'Empresa Admin'

        checkout = Checkout()
        admin, op_id, op_nome = await checkout._resolve_operator(
            current_user, None
        )

        self.assertEqual(admin.id, 1)
        self.assertEqual(op_nome, 'Empresa Admin')

    async def test_process_sale_missing_params(self):
        """Garante erro 400 ao tentar vender sem dados essenciais."""
        checkout = Checkout()
        with self.assertRaises(HTTPException) as cm:
            await checkout.process_sale(
                current_user=MagicMock(),
                product_code='',
                quantity=0,
                payment_method='',
            )
        self.assertEqual(cm.exception.status_code, 400)

    @patch('src.controllers.sales.sales.Checkout._resolve_operator')
    @patch('src.controllers.sales.sales.Checkout.get_product_by_user')
    @patch('src.controllers.sales.sales.Sales.create', new_callable=AsyncMock)
    @patch('src.controllers.sales.sales.build_receipt', new_callable=AsyncMock)
    @patch('src.controllers.sales.sales.in_transaction')
    async def test_process_sale_success(
        self,
        mock_in_transaction,
        mock_build_receipt,
        mock_sales_create,
        mock_get_product,
        mock_resolve_operator,
    ):
        """Teste de fluxo completo: resolve operador, baixa estoque e registra venda."""
        mock_in_transaction.return_value.__aenter__ = AsyncMock()
        mock_in_transaction.return_value.__aexit__ = AsyncMock()

        admin_user = MagicMock()
        admin_user.id = 1
        mock_resolve_operator.return_value = (admin_user, 1, 'Operador')

        mock_product = MagicMock()
        mock_product.stock = 100
        mock_product.sale_price = 10.0
        mock_product.cost_price = 5.0
        mock_product.save = AsyncMock()
        mock_get_product.return_value = mock_product

        mock_sales_create.return_value = MagicMock(id=50)
        mock_build_receipt.return_value = ({'msg': 'Recibo OK'}, True)

        checkout = Checkout()
        receipt, status = await checkout.process_sale(
            current_user=admin_user,
            product_code='P1',
            quantity=10,
            payment_method='PIX',
        )

        self.assertTrue(status)
        self.assertEqual(mock_product.stock, 90)
        mock_product.save.assert_called_once()

    @patch('src.controllers.sales.sales.Checkout._resolve_operator')
    @patch(
        'src.controllers.sales.sales.Checkout.get_product_by_user',
        new_callable=AsyncMock,
    )
    @patch('src.controllers.sales.sales.in_transaction')
    async def test_process_sale_insufficient_stock(
        self, mock_in_transaction, mock_get_product, mock_resolve_operator
    ):
        """Valida que a venda e bloqueada se o estoque for insuficiente."""
        # 1. Mock do contexto de transacao
        mock_in_transaction.return_value.__aenter__ = AsyncMock()
        mock_in_transaction.return_value.__aexit__ = AsyncMock()

        # 2. Mock do operador
        admin_user = MagicMock()
        admin_user.id = 1
        mock_resolve_operator.return_value = (admin_user, None, 'Admin')

        # 3. Mock do produto com estoque insuficiente (estoque = 5)
        mock_product = MagicMock()
        mock_product.stock = 5
        mock_product.sale_price = 10.0
        mock_product.cost_price = 5.0

        # Garantir que o mock do get_product_by_user retorne o produto
        mock_get_product.return_value = mock_product

        checkout = Checkout()

        # 4. Execucao esperando falha (solicitando 10 unidades para estoque de 5)
        with self.assertRaises(HTTPException) as cm:
            await checkout.process_sale(
                current_user=admin_user,
                product_code='PROD_LOW',
                quantity=10,
                payment_method='PIX',
            )

        self.assertEqual(cm.exception.status_code, 400)
        self.assertIn('Estoque insuficiente', cm.exception.detail)


if __name__ == '__main__':
    unittest.main(verbosity=2)
