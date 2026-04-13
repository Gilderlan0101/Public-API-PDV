import json
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ajuste de Path
DIR_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DIR_ROOT) not in sys.path:
    sys.path.append(str(DIR_ROOT))

from src.model.product import Produto
from src.utils.get_produtos_user import get_product_by_user


class TestBuscarProduto(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Patch centralizado para o Redis (evita erro de Event Loop closed)
        self.patcher_redis = patch('src.utils.get_produtos_user.client')
        self.mock_redis = self.patcher_redis.start()

        # Mocks padrão para o Redis
        self.mock_redis.get = AsyncMock(return_value=None)
        self.mock_redis.setex = AsyncMock()

    def tearDown(self):
        self.patcher_redis.stop()

    async def test_busca_por_codigo_sucesso(self):
        """Testa a busca de um produto existente via código."""
        fake_data = {
            'id': 1,
            'name': 'Coca-Cola 2L',
            'product_code': 'BEB001',
            'usuario_id': 1,
        }

        # Criamos a estrutura que o Tortoise esperaria: um objeto com método .values()
        mock_obj_with_values = MagicMock()
        mock_obj_with_values.values = AsyncMock(return_value=fake_data)

        # O first() retorna esse objeto
        mock_first = AsyncMock(return_value=mock_obj_with_values)

        with patch.object(Produto, 'filter') as mock_filter:
            # Simula: Produto.filter().filter().first()
            mock_filter.return_value.filter.return_value.first = mock_first

            result = await get_product_by_user(user_id=1, code='BEB001')

            self.assertIsNotNone(result)
            self.assertEqual(result['name'], 'Coca-Cola 2L')
            self.assertEqual(result['product_code'], 'BEB001')

    async def test_busca_por_nome_sucesso(self):
        """Testa a busca de um produto existente via nome."""
        fake_data = {
            'id': 2,
            'name': 'Suco de Laranja 1L',
            'product_code': 'BEB002',
            'usuario_id': 1,
        }

        mock_obj_with_values = MagicMock()
        mock_obj_with_values.values = AsyncMock(return_value=fake_data)
        mock_first = AsyncMock(return_value=mock_obj_with_values)

        with patch.object(Produto, 'filter') as mock_filter:
            mock_filter.return_value.filter.return_value.first = mock_first

            result = await get_product_by_user(
                user_id=1, name='Suco de Laranja 1L'
            )

            self.assertIsNotNone(result)
            self.assertEqual(result['product_code'], 'BEB002')

    async def test_retorno_via_cache_redis(self):
        """Testa se a função retorna os dados do Redis sem consultar o banco."""
        fake_cache_data = {'id': 10, 'name': 'Produto do Cache'}
        self.mock_redis.get.return_value = json.dumps(fake_cache_data)

        # Se o cache retornar dados, a função nem deve chegar no Produto.filter
        with patch.object(Produto, 'filter') as mock_filter:
            result = await get_product_by_user(user_id=1, code='CACHE123')

            self.assertEqual(result['name'], 'Produto do Cache')
            mock_filter.assert_not_called()

    async def test_retorna_none_quando_nao_encontra(self):
        """Testa o comportamento quando o produto não existe no banco."""
        # Se não encontra nada, o Tortoise retorna None no .first()
        mock_first = AsyncMock(return_value=None)

        with patch.object(Produto, 'filter') as mock_filter:
            mock_filter.return_value.filter.return_value.first = mock_first

            result = await get_product_by_user(user_id=1, code='NAO_EXISTE')
            self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
