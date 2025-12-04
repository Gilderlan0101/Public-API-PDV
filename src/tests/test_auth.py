import os
import sys
import unittest

from src.auth.auth_jwt import get_hashed_password, verify_password

sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
)


class TestAuth(unittest.TestCase):
    def setUp(self):
        self.password = 'senhateste123'
        self.hashed = get_hashed_password(self.password)

    def test_create_hash(self):
        self.assertIsNotNone(self.hashed)
        # Hash não pode ser igual à senha original
        self.assertNotEqual(self.password, self.hashed)

    def test_verify_hash(self):
        self.assertTrue(verify_password(self.password, self.hashed))
        self.assertFalse(verify_password('senhaerrada', self.hashed))


if __name__ == '__main__':
    # Limpa antes de começar
    os.system('clear')
    print('Realizando teste de hash em senhas...\n')

    # Executa os testes
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(TestAuth)
    )

    # Se todos passaram
    if result.wasSuccessful():
        print('\n✅ Todos os testes passaram com sucesso!')
        input('\nPressione Enter para continuar...')
        os.system('clear')
    else:
        print('\n❌ Alguns testes falharam.')
