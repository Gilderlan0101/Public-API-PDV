import os
import sys
import asyncio
import random
import re
from pathlib import Path
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Configuracao de path para reconhecimento do modulo src
DIR_ROOT = Path(__file__).resolve().parent.parent.parent
if str(DIR_ROOT) not in sys.path:
    sys.path.append(str(DIR_ROOT))

from faker import Faker
from tortoise import Tortoise
from tortoise.transactions import in_transaction

# Importacoes do projeto
from src.auth.auth_jwt import get_hashed_password
from src.controllers.payments.pix import PixCreateRequest, PixService
from src.model.caixa import Caixa
from src.model.customers import Customer
from src.model.employee import Employees
from src.model.product import Produto
from src.model.user import Usuario
from src.logs.infos import LOGGER
from src.conf.database import TORTOISE_ORM

# Configuracoes globais
FAKE = Faker('pt_BR')
TZ = ZoneInfo('America/Sao_Paulo')


async def setup_database():
    """Inicializa a conexao com o Tortoise ORM."""
    try:
        await Tortoise.init(config=TORTOISE_ORM)
        LOGGER.info(
            'Banco de dados inicializado para insercao de dados de teste.'
        )
    except Exception as e:
        LOGGER.error(f'Erro ao inicializar Tortoise: {e}')
        raise


async def create_caixa_for_employee(funcionario: Employees, usuario_id: int):
    """Cria automaticamente um caixa para um funcionario."""
    try:
        from src.utils.sales_code_generator import generator_code_to_checkout

        caixa_id = await generator_code_to_checkout(usuario_id)

        return await Caixa.create(
            nome=f'Caixa - {funcionario.nome}',
            saldo_inicial=0.0,
            saldo_atual=0.0,
            aberto=False,
            caixa_id=caixa_id,
            usuario_id=usuario_id,
            funcionario_id=funcionario.id,
            valor_total=0.0,
        )
    except Exception as e:
        print(f'Erro ao criar caixa para {funcionario.nome}: {e}')
        return None


async def seed_users():
    """Cria os usuarios admin (empresas)."""
    # Empresa 1
    admin, _ = await Usuario.get_or_create(
        email='admin@dev.com',
        defaults={
            'username': 'Gilderlna',
            'password': get_hashed_password('mobilador001'),
            'company_name': 'dev Orbit',
            'trade_name': 'dev Orbit',
            'membros': 0,
            'cnpj': '12345678912345',
            'city': 'Ibirataia',
            'state': 'BA',
            'pending': True,
        },
    )

    # Empresa 2
    admin_2, _ = await Usuario.get_or_create(
        email='silva@test.com',
        defaults={
            'username': 'Restaurante',
            'password': get_hashed_password('123456'),
            'company_name': 'Restaurante da Maria',
            'trade_name': 'Restaurante Maria',
            'membros': 1,
            'cnpj': '98765432000198',
            'city': 'Rio de Janeiro',
            'state': 'RJ',
            'pending': True,
        },
    )
    print('Usuarios admin verificados/criados.')
    return admin, admin_2


async def seed_employees(admin_1: Usuario, admin_2: Usuario):
    """Cria funcionarios e seus caixas."""
    funcionarios = [
        {
            'nome': 'Carlos Caixa',
            'email': 'carlos.caixa@empresa1.com',
            'adm': admin_1,
        },
        {
            'nome': 'Roberto Caixa',
            'email': 'roberto.caixa@empresa2.com',
            'adm': admin_2,
        },
    ]

    for f_data in funcionarios:
        funcionario, created = await Employees.get_or_create(
            email=f_data['email'],
            defaults={
                'nome': f_data['nome'],
                'cargo': 'Caixa',
                'senha': get_hashed_password('1234'),
                'telefone': FAKE.cellphone_number(),
                'ativo': True,
                'usuario_id': f_data['adm'].id,
            },
        )
        if created:
            await create_caixa_for_employee(funcionario, f_data['adm'].id)
    print('Funcionarios e caixas verificados/criados.')


async def seed_customers(admin_1: Usuario, admin_2: Usuario):
    """Gera clientes ficticios garantindo campos obrigatorios como due_date."""
    for adm in [admin_1, admin_2]:
        for _ in range(3):
            cpf = re.sub(r'\D', '', FAKE.unique.cpf())
            # Convertendo datas para objetos datetime cientes do fuso horario
            data_nascimento = datetime.combine(
                FAKE.date_of_birth(minimum_age=18), datetime.min.time()
            ).replace(tzinfo=TZ)
            data_vencimento = datetime.now(TZ) + timedelta(days=30)

            await Customer.create(
                full_name=FAKE.name(),
                birth_date=data_nascimento,
                cpf=cpf,
                road=FAKE.street_name(),
                house_number=str(random.randint(1, 999)),
                neighborhood=FAKE.bairro(),
                city=FAKE.city(),
                tel=FAKE.cellphone_number()[:20],
                cep=FAKE.postcode()[:10],
                credit=1000.0,
                due_date=data_vencimento,  # Correcao do IntegrityError
                usuario=adm,
            )
    print('Clientes registrados com sucesso.')


async def run_seed():
    """Execucao principal do seed."""
    await setup_database()

    try:
        async with in_transaction():
            admin_1, admin_2 = await seed_users()
            await seed_employees(admin_1, admin_2)
            await seed_customers(admin_1, admin_2)

        print('\nProcesso de carga de dados finalizado.')
    except Exception as e:
        print(f'Erro durante o seed: {e}')
    finally:
        await Tortoise.close_connections()


if __name__ == '__main__':
    asyncio.run(run_seed())
