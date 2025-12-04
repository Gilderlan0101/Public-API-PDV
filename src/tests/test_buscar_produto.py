import unittest
from unittest.mock import AsyncMock, patch

from src.model.product import Produto
from src.utils.get_produtos_user import get_product_by_user


class TestBuscarProduto(unittest.IsolatedAsyncioTestCase):
    async def test_busca_por_codigo(self):
        fake_produto = Produto(
            id=1, name='Coca-Cola 2L', product_code='BEB001', usuario_id=1
        )

        # Mocka apenas first(), que é async
        mock_first = AsyncMock(return_value=fake_produto)
        with patch.object(Produto, 'filter') as mock_filter:
            mock_filter.return_value.filter.return_value.first = mock_first

            result = await get_product_by_user(user_id=1, code='BEB001')

            self.assertIsNotNone(result)
            self.assertEqual(result.name, 'Coca-Cola 2L')
            mock_filter.assert_called_once_with(usuario_id=1)

    async def test_busca_por_nome(self):
        fake_produto = Produto(
            id=2,
            name='Suco de Laranja 1L',
            product_code='BEB002',
            usuario_id=1,
        )

        mock_first = AsyncMock(return_value=fake_produto)
        with patch.object(Produto, 'filter') as mock_filter:
            mock_filter.return_value.filter.return_value.first = mock_first

            result = await get_product_by_user(
                user_id=1, name='Suco de Laranja 1L'
            )

            self.assertIsNotNone(result)
            self.assertEqual(result.product_code, 'BEB002')
            mock_filter.assert_called_once_with(usuario_id=1)

    async def test_retorna_none_quando_nao_encontra(self):
        mock_first = AsyncMock(return_value=None)
        with patch.object(Produto, 'filter') as mock_filter:
            mock_filter.return_value.filter.return_value.first = mock_first

            result = await get_product_by_user(user_id=1, code='NAOEXISTE')

            self.assertIsNone(result)
            mock_filter.assert_called_once_with(usuario_id=1)


if __name__ == '__main__':
    unittest.main()
