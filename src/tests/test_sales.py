import unittest
from dataclasses import is_dataclass

from fastapi import HTTPException

from src.controllers.sales.sales import Checkout


class TestProduct(unittest.IsolatedAsyncioTestCase):
    def test_if_it_is_a_dataclass(self):
        self.assertTrue(is_dataclass(Checkout))

    async def asyncSetUp(self):
        self.checkout = Checkout(
            user_id=1,
            product_name='Coca-Cola 2L',
            produto_id=1,
            quantity=10,
            payment_method='PIX',
            total_price=100.0,
            lucro_total=40.0,
            funcionario_id=1,
        )

    async def test_constructor(self):
        self.assertEqual(self.checkout.user_id, 1)
        self.assertEqual(self.checkout.product_name, 'Coca-Cola 2L')
        self.assertEqual(self.checkout.quantity, 10)
        self.assertEqual(self.checkout.total_price, 100.0)
        self.assertEqual(self.checkout.lucro_total, 40.0)
        self.assertEqual(self.checkout.payment_method, 'PIX')

    async def test_verify_datas_raises_when_user_id_missing(self):
        checkout = Checkout(
            user_id=0,
            product_name='Produto X',
            quantity=1,
            payment_method='PIX',
        )
        with self.assertRaises(HTTPException) as cm:
            await checkout.verify_datas()
        self.assertEqual(cm.exception.status_code, 401)

    async def test_verify_datas_raises_when_missing_fields(self):
        checkout = Checkout(
            user_id=1, product_name='', quantity=0, payment_method='PIX'
        )
        with self.assertRaises(HTTPException) as cm:
            await checkout.verify_datas()
        self.assertEqual(cm.exception.status_code, 400)


if __name__ == '__main__':
    unittest.main()
