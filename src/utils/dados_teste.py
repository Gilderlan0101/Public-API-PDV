import json
import os
import random
import re
import time
from datetime import datetime

from dotenv import load_dotenv
from faker import Faker
from fastapi import HTTPException
from passlib.hash import bcrypt
from tortoise.expressions import F
from tortoise.transactions import in_transaction

from src.auth.auth_jwt import get_hashed_password
from src.controllers.caixa.cash_controller import FinalizationObjcts
from src.controllers.car.cart_control import CartManagerDB
from src.controllers.delivery.delivery_controller import CreateDelivery
from src.controllers.delivery.delivery_reports import (
    assign_delivery_to_driver,
    gerenciagelivery,
    update_delivery_status,
)
from src.controllers.payments.pix import PixCreateRequest, PixService
from src.controllers.sales.sales import Checkout
from src.controllers.sales.services import processar_venda_carrinho
from src.model.caixa import Caixa
from src.model.cashmovement import CashMovement
from src.model.customers import Customer
from src.model.employee import Employees
from src.model.partial import Partial
from src.model.product import Produto
from src.model.user import Membro, Usuario
from src.utils.sales_code_generator import lot_bar_code_size

__PAYMENT_METHODS = ['PIX', 'CARTAO', 'DINHEIRO', 'NOTA', 'FIADO']
IMG_PRODUCT_DEFAULT = os.getenv('PATH_IMG_DEFAULT_PRODUCTS', None)

load_dotenv()


async def create_mock_data_and_sell_all_stock():
    """Cria dados mockados completos para duas empresas com funcionários e caixas automáticos"""
    fake = Faker('pt_BR')

    async with in_transaction() as conn:
        # ========================
        # Criar usuários admin (empresas)
        # ========================
        admin = await Usuario.filter(email='admin@test.com').first()
        if not admin:
            print('🔹 Criando usuário admin...')
            admin = await Usuario.create(
                username='Gilderlna',
                email='admin@dev.com',
                password=get_hashed_password('mobilador001'),
                company_name='dev Orbit',
                trade_name='dev Orbit',
                membros=0,
                cnpj='12345678912345',
                city='Ibirataia',
                state='BA',
                pending=True,
            )
            print(f'✅ Usuário admin criado: {admin.email}')

        admin_2 = await Usuario.filter(email='silva@test.com').first()
        if not admin_2:
            print('🔹 Criando usuário admin silva...')
            admin_2 = await Usuario.create(
                username='Restaurante',
                email='silva@test.com',
                password=get_hashed_password('123456'),
                company_name='Restaurante da Maria',
                trade_name='Restaurante Maria',
                membros=1,
                cnpj='98765432000198',
                city='Rio de Janeiro',
                state='RJ',
                pending=True,
            )
            print(f'✅ Usuário admin 2 criado: {admin_2.email}')

        # ========================
        # CRIAR CONTAS PIX PARA AMBAS AS EMPRESAS
        # ========================
        print('\n🔹 Criando contas PIX...')

        # Conta PIX para empresa 1
        pix_service_1 = PixService(user_id=admin.id)
        pix_data_1 = PixCreateRequest(
            full_name='João Silva santos',
            city='São Paulo',
            key_pix='11999999999',
            value=1.0,
            type_exit='qr',
        )

        try:
            conta_pix_1 = await pix_service_1.create_pix_account(pix_data_1)
            if conta_pix_1:
                print(
                    f'✅ Conta PIX criada para Empresa 1: {pix_data_1.key_pix}'
                )
            else:
                print('❌ Erro ao criar conta PIX para Empresa 1')
        except Exception as e:
            print(f'⚠️  Erro ao criar conta PIX Empresa 1: {str(e)}')

        # Conta PIX para empresa 2
        pix_service_2 = PixService(user_id=admin_2.id)
        pix_data_2 = PixCreateRequest(
            full_name='Maria Santos migel',
            city='Rio de Janeiro',
            key_pix='21988888888',
            value=1.0,
            type_exit='qr',
        )

        try:
            conta_pix_2 = await pix_service_2.create_pix_account(pix_data_2)
            if conta_pix_2:
                print(
                    f'✅ Conta PIX criada para Empresa 2: {pix_data_2.key_pix}'
                )
            else:
                print('❌ Erro ao criar conta PIX para Empresa 2')
        except Exception as e:
            print(f'⚠️  Erro ao criar conta PIX Empresa 2: {str(e)}')

        # ========================
        # Criar funcionários para AMBAS as empresas
        # ========================
        print('\n🔹 Criando funcionários para ambas as empresas...')

        # Funcionários Empresa 1 (Pizzaria do João)
        funcionarios_empresa1 = [
            {
                'nome': 'Carlos Caixa',
                'email': '                                                                                                                                                                                                     ',
                'cargo': 'Caixa',
                'senha': '1234',
            },
            {
                'nome': 'Ana Atendente',
                'email': 'ana.atendente@empresa1.com',
                'cargo': 'Atendente',
                'senha': '1234',
            },
            {
                'nome': 'Pedro Entregador',
                'email': 'pedro.entregador@empresa1.com',
                'cargo': 'Entregador',
                'senha': '1234',
            },
            {
                'nome': 'Mariana Gerente',
                'email': 'mariana.gerente@empresa1.com',
                'cargo': 'Gerente',
                'senha': '1234',
            },
        ]

        # Funcionários Empresa 2 (Restaurante da Maria)
        funcionarios_empresa2 = [
            {
                'nome': 'Roberto Caixa',
                'email': 'roberto.caixa@empresa2.com',
                'cargo': 'Caixa',
                'senha': '1234',
            },
            {
                'nome': 'Carla Atendente',
                'email': 'carla.atendente@empresa2.com',
                'cargo': 'Atendente',
                'senha': '1234',
            },
            {
                'nome': 'Lucas Entregador',
                'email': 'lucas.entregador@empresa2.com',
                'cargo': 'Entregador',
                'senha': '1234',
            },
            {
                'nome': 'Fernanda Cozinheira',
                'email': 'fernanda.cozinheira@empresa2.com',
                'cargo': 'Cozinheira',
                'senha': '1234',
            },
        ]

        funcionarios_criados_emp1 = []
        funcionarios_criados_emp2 = []

        # Criar funcionários Empresa 1
        for func in funcionarios_empresa1:
            funcionario = await Employees.filter(email=func['email']).first()
            if not funcionario:
                funcionario = await Employees.create(
                    nome=func['nome'],
                    cargo=func['cargo'],
                    email=func['email'],
                    senha=get_hashed_password(func['senha']),
                    telefone=fake.cellphone_number(),
                    ativo=True,
                    usuario_id=admin.id,
                )
                print(
                    f'✅ Funcionário Empresa 1 criado: {funcionario.nome} - {funcionario.cargo}'
                )

                # Se for Caixa, cria automaticamente o caixa
                if func['cargo'].lower() == 'caixa':
                    await create_caixa_for_employee(funcionario, admin.id)

                funcionarios_criados_emp1.append(funcionario)

        # Criar funcionários Empresa 2
        for func in funcionarios_empresa2:
            funcionario = await Employees.filter(email=func['email']).first()
            if not funcionario:
                funcionario = await Employees.create(
                    nome=func['nome'],
                    cargo=func['cargo'],
                    email=func['email'],
                    senha=get_hashed_password(func['senha']),
                    telefone=fake.cellphone_number(),
                    ativo=True,
                    usuario_id=admin_2.id,
                )
                print(
                    f'✅ Funcionário Empresa 2 criado: {funcionario.nome} - {funcionario.cargo}'
                )

                # Se for Caixa, cria automaticamente o caixa
                if func['cargo'].lower() == 'caixa':
                    await create_caixa_for_employee(funcionario, admin_2.id)

                funcionarios_criados_emp2.append(funcionario)

        # ========================
        # Criar produtos para AMBAS as empresas
        # ========================
        print('\n🔹 Criando produtos para ambas as empresas...')

        # Produtos comuns para ambas as empresas
        produtos_data_comuns = [
            {
                'code': 'BEB001',
                'name': 'Coca-Cola 2L',
                'cost': 5.50,
                'sale': 8.00,
                'supplier': 'Coca-Cola',
                'group': 'Bebidas',
            },
            {
                'code': 'BEB002',
                'name': 'Guaraná 2L',
                'cost': 4.50,
                'sale': 7.00,
                'supplier': 'Antarctica',
                'group': 'Bebidas',
            },
            {
                'code': 'BEB003',
                'name': 'Água Mineral 500ml',
                'cost': 1.50,
                'sale': 3.00,
                'supplier': 'Crystal',
                'group': 'Bebidas',
            },
        ]

        # Produtos exclusivos Empresa 1 (Pizzaria)
        produtos_exclusivos_empresa1 = [
            {
                'code': 'PIZ001',
                'name': 'Pizza Calabresa',
                'cost': 15.00,
                'sale': 25.00,
                'supplier': 'Forninho',
                'group': 'Pizzas',
            },
            {
                'code': 'PIZ002',
                'name': 'Pizza Frango Catupiry',
                'cost': 16.00,
                'sale': 26.00,
                'supplier': 'Forninho',
                'group': 'Pizzas',
            },
            {
                'code': 'PIZ003',
                'name': 'Pizza Portuguesa',
                'cost': 17.00,
                'sale': 27.00,
                'supplier': 'Forninho',
                'group': 'Pizzas',
            },
            {
                'code': 'PIZ004',
                'name': 'Pizza Margherita',
                'cost': 14.00,
                'sale': 24.00,
                'supplier': 'Forninho',
                'group': 'Pizzas',
            },
            {
                'code': 'PIZ005',
                'name': 'Pizza Quatro Queijos',
                'cost': 18.00,
                'sale': 28.00,
                'supplier': 'Forninho',
                'group': 'Pizzas',
            },
            {
                'code': 'ESF001',
                'name': 'Esfiha de Carne',
                'cost': 3.00,
                'sale': 6.00,
                'supplier': 'Forninho',
                'group': 'Esfihas',
            },
            {
                'code': 'ESF002',
                'name': 'Esfiha de Queijo',
                'cost': 2.50,
                'sale': 5.00,
                'supplier': 'Forninho',
                'group': 'Esfihas',
            },
        ]

        # Produtos exclusivos Empresa 2 (Restaurante)
        produtos_exclusivos_empresa2 = [
            {
                'code': 'PRT001',
                'name': 'Filé Mignon',
                'cost': 25.00,
                'sale': 45.00,
                'supplier': 'Açougue',
                'group': 'Pratos Principais',
            },
            {
                'code': 'PRT002',
                'name': 'Frango Grelhado',
                'cost': 12.00,
                'sale': 22.00,
                'supplier': 'Açougue',
                'group': 'Pratos Principais',
            },
            {
                'code': 'PRT003',
                'name': 'Salmão ao Molho',
                'cost': 20.00,
                'sale': 38.00,
                'supplier': 'Peixaria',
                'group': 'Pratos Principais',
            },
            {
                'code': 'SAL001',
                'name': 'Salada Caesar',
                'cost': 8.00,
                'sale': 15.00,
                'supplier': 'Hortifruti',
                'group': 'Saladas',
            },
            {
                'code': 'SAL002',
                'name': 'Salada Verde',
                'cost': 6.00,
                'sale': 12.00,
                'supplier': 'Hortifruti',
                'group': 'Saladas',
            },
            {
                'code': 'SOB001',
                'name': 'Pudim de Leite',
                'cost': 4.00,
                'sale': 8.00,
                'supplier': 'Confeitaria',
                'group': 'Sobremesas',
            },
            {
                'code': 'SOB002',
                'name': 'Mousse de Chocolate',
                'cost': 3.50,
                'sale': 7.00,
                'supplier': 'Confeitaria',
                'group': 'Sobremesas',
            },
        ]

        produtos_criados_empresa1 = []
        produtos_criados_empresa2 = []

        # Criar produtos comuns para ambas as empresas
        for p in produtos_data_comuns:
            # Para empresa 1
            produto_emp1 = await Produto.filter(
                product_code=p['code'], usuario_id=admin.id
            ).first()
            if not produto_emp1:
                produto_emp1 = await Produto.create(
                    product_code=p['code'],
                    name=p['name'],
                    stock=random.randint(50, 100),
                    stoke_max=200,
                    stoke_min=10,
                    cost_price=p['cost'],
                    price_uni=p['cost'] * 1.2,
                    sale_price=p['sale'],
                    supplier=p['supplier'],
                    ticket='Sim',
                    controllstoke='Sim',
                    group=p['group'],
                    image_url=IMG_PRODUCT_DEFAULT,
                    usuario_id=admin.id,
                )
                print(f"✅ Produto comum Empresa 1: {p['name']}")
            produtos_criados_empresa1.append(produto_emp1)

            # Para empresa 2
            produto_emp2 = await Produto.filter(
                product_code=p['code'], usuario_id=admin_2.id
            ).first()
            if not produto_emp2:
                produto_emp2 = await Produto.create(
                    product_code=p['code'],
                    name=p['name'],
                    stock=random.randint(50, 100),
                    stoke_max=200,
                    stoke_min=10,
                    cost_price=p['cost'],
                    price_uni=p['cost'] * 1.2,
                    sale_price=p['sale'],
                    supplier=p['supplier'],
                    ticket='Sim',
                    controllstoke='Sim',
                    group=p['group'],
                    image_url=IMG_PRODUCT_DEFAULT,
                    usuario_id=admin_2.id,
                )
                print(f"✅ Produto comum Empresa 2: {p['name']}")
            produtos_criados_empresa2.append(produto_emp2)

        # Criar produtos exclusivos para empresa 1
        for p in produtos_exclusivos_empresa1:
            produto = await Produto.filter(
                product_code=p['code'], usuario_id=admin.id
            ).first()
            if not produto:
                produto = await Produto.create(
                    product_code=p['code'],
                    name=p['name'],
                    stock=random.randint(30, 80),
                    stoke_max=150,
                    stoke_min=5,
                    cost_price=p['cost'],
                    price_uni=p['cost'] * 1.2,
                    sale_price=p['sale'],
                    supplier=p['supplier'],
                    ticket='Sim',
                    controllstoke='Sim',
                    group=p['group'],
                    image_url=IMG_PRODUCT_DEFAULT,
                    usuario_id=admin.id,
                )
                print(f"✅ Produto exclusivo Empresa 1: {p['name']}")
                produtos_criados_empresa1.append(produto)

        # Criar produtos exclusivos para empresa 2
        for p in produtos_exclusivos_empresa2:
            produto = await Produto.filter(
                product_code=p['code'], usuario_id=admin_2.id
            ).first()
            if not produto:
                produto = await Produto.create(
                    product_code=p['code'],
                    name=p['name'],
                    stock=random.randint(30, 80),
                    stoke_max=150,
                    stoke_min=5,
                    cost_price=p['cost'],
                    price_uni=p['cost'] * 1.2,
                    sale_price=p['sale'],
                    supplier=p['supplier'],
                    ticket='Sim',
                    controllstoke='Sim',
                    group=p['group'],
                    image_url=IMG_PRODUCT_DEFAULT,
                    usuario_id=admin_2.id,
                )
                print(f"✅ Produto exclusivo Empresa 2: {p['name']}")
                produtos_criados_empresa2.append(produto)

        # ========================
        # Criar clientes para ambas as empresas
        # ========================
        print('\n🔹 Criando clientes para ambas as empresas...')

        clientes_empresa1 = []
        clientes_empresa2 = []

        # Clientes Empresa 1 (São Paulo)
        for i in range(5):
            cpf_numbers_only = re.sub(r'\D', '', fake.cpf())
            cliente = await Customer.create(
                full_name=fake.name(),
                birth_date=fake.date_of_birth(
                    minimum_age=18, maximum_age=60
                ).isoformat(),
                cpf=cpf_numbers_only,
                mother_name=fake.name_female(),
                road=fake.street_name(),
                house_number=str(random.randint(1, 1000)),
                neighborhood=fake.bairro(),
                city='São Paulo',
                tel=fake.cellphone_number(),
                cep=fake.postcode(),
                credit=1000.00,
                current_balance=0.00,
                due_date=datetime.now(),
                status='ATIVO',
                usuario_id=admin.id,
            )
            clientes_empresa1.append(cliente)
            print(f'✅ Cliente Empresa 1: {cliente.full_name}')

        # Clientes Empresa 2 (Rio de Janeiro)
        for i in range(5):
            cpf_numbers_only = re.sub(r'\D', '', fake.cpf())
            cliente = await Customer.create(
                full_name=fake.name(),
                birth_date=fake.date_of_birth(
                    minimum_age=18, maximum_age=60
                ).isoformat(),
                cpf=cpf_numbers_only,
                mother_name=fake.name_female(),
                road=fake.street_name(),
                house_number=str(random.randint(1, 1000)),
                neighborhood=fake.bairro(),
                city='Rio de Janeiro',
                tel=fake.cellphone_number(),
                cep=fake.postcode(),
                credit=1000.00,
                current_balance=0.00,
                due_date=datetime.now(),
                status='ATIVO',
                usuario_id=admin_2.id,
            )
            clientes_empresa2.append(cliente)
            print(f'✅ Cliente Empresa 2: {cliente.full_name}')

        # ========================
        # VERIFICAR CAIXAS CRIADOS AUTOMATICAMENTE (CORRIGIDO)
        # ========================
        print('\n🔹 Verificando caixas criados automaticamente...')

        # Use prefetch_related para carregar os relacionamentos
        caixas_empresa1 = (
            await Caixa.filter(usuario_id=admin.id)
            .prefetch_related('funcionario')
            .all()
        )
        caixas_empresa2 = (
            await Caixa.filter(usuario_id=admin_2.id)
            .prefetch_related('funcionario')
            .all()
        )

        print(f'🏢 Empresa 1 - Caixas criados: {len(caixas_empresa1)}')
        for caixa in caixas_empresa1:
            funcionario_nome = (
                caixa.funcionario.nome
                if caixa.funcionario
                else 'Sem funcionário'
            )
            print(f'   • Caixa ID: {caixa.caixa_id} - {funcionario_nome}')

        print(f'🏢 Empresa 2 - Caixas criados: {len(caixas_empresa2)}')
        for caixa in caixas_empresa2:
            funcionario_nome = (
                caixa.funcionario.nome
                if caixa.funcionario
                else 'Sem funcionário'
            )
            print(f'   • Caixa ID: {caixa.caixa_id} - {funcionario_nome}')

        # ========================
        # RESUMO FINAL
        # ========================
        print('\n' + '=' * 60)
        print('📊 RESUMO FINAL DOS DADOS CRIADOS')
        print('=' * 60)

        print(f'\n🏢 EMPRESA 1: {admin.company_name}')
        print(f'   📧 Email: {admin.email}')
        print(f'   👥 Funcionários: {len(funcionarios_criados_emp1)}')
        print(f'   🏪 Caixas: {len(caixas_empresa1)}')
        print(f'   🛍️  Produtos: {len(produtos_criados_empresa1)}')
        print(f'   👤 Clientes: {len(clientes_empresa1)}')
        print(f'   💰 Conta PIX: {pix_data_1.key_pix}')

        print(f'\n🏢 EMPRESA 2: {admin_2.company_name}')
        print(f'   📧 Email: {admin_2.email}')
        print(f'   👥 Funcionários: {len(funcionarios_criados_emp2)}')
        print(f'   🏪 Caixas: {len(caixas_empresa2)}')
        print(f'   🛍️  Produtos: {len(produtos_criados_empresa2)}')
        print(f'   👤 Clientes: {len(clientes_empresa2)}')
        print(f'   💰 Conta PIX: {pix_data_2.key_pix}')

        print(f'\n🎉 Dados de teste criados com sucesso!')
        print(f'💡 Use os emails e senhas abaixo para testar o sistema:')
        print(f'   Empresa 1: {admin.email} / 123456')
        print(f'   Empresa 2: {admin_2.email} / 123456')
        print(f'   Funcionários Caixa: Use email do funcionário / 1234')


async def create_caixa_for_employee(funcionario: Employees, usuario_id: int):
    """
    Cria automaticamente um caixa para um funcionário com cargo "Caixa"
    """
    try:
        from src.utils.sales_code_generator import generator_code_to_checkout

        # Gera um caixa_id único para esta empresa
        caixa_id = await generator_code_to_checkout(usuario_id)

        # Cria o caixa
        novo_caixa = await Caixa.create(
            nome=f'Caixa - {funcionario.nome}',
            saldo_inicial=0.0,
            saldo_atual=0.0,
            aberto=False,
            caixa_id=caixa_id,
            usuario_id=usuario_id,
            funcionario_id=funcionario.id,
            valor_total=0.0,
        )

        print(f'   ✅ Caixa criado para {funcionario.nome}: ID {caixa_id}')
        return novo_caixa

    except Exception as e:
        print(f'   ❌ Erro ao criar caixa para {funcionario.nome}: {e}')
        return None


async def testar_sistema_entrega(
    company_id: int, clientes: list, produtos: list
):
    """Executa testes específicos do sistema de entrega"""
    print(f'\n🚀 Testando sistema de entrega para empresa {company_id}...')
    # Aqui você pode adicionar testes específicos de entrega se necessário
    pass
