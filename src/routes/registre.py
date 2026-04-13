import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from tortoise.transactions import in_transaction

from src.auth.auth_jwt import get_hashed_password
from src.logs.infos import LOGGER
# Importações de modelos e utilitários
from src.model.caixa import Caixa
from src.model.employee import Employees
from src.model.tickets import criar_tickets_padrao
from src.model.user import CNPJCache, Usuario
from src.schemas.schema_user import CompanyRegisterSchema
from src.services.consulting_cnpj import consulting_CNPJ
from src.utils.sales_code_generator import generator_code_to_checkout

# Configuração do Router
registration_router = APIRouter(tags=['Authentication'])


@registration_router.post('/register', status_code=status.HTTP_201_CREATED)
async def register_company(user: CompanyRegisterSchema):
    """
    Registra uma nova empresa, cria um funcionário administrador padrão
    e inicializa o primeiro caixa (PDV) do sistema.
    """

    # 1. Verificação de existência
    existing_user = await Usuario.filter(email=user.email).first()
    if existing_user:
        LOGGER.warning(f'Falha no registro: Email {user.email} já cadastrado.')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email já cadastrado.',
        )

    # 2. Criptografia da senha
    hashed_password = get_hashed_password(user.pwd)

    try:
        async with in_transaction() as conn:
            # 3. Criação da Empresa (Usuário Admin)
            new_user = await Usuario.create(
                username=user.full_name,
                email=user.email,
                password=hashed_password,
                company_name=user.company_name,
                trade_name=getattr(user, 'trade_name', None),
                membros=getattr(user, 'membros', 0),
                cpf=user.cpf,
                cnpj=user.cnpj,
                state_registration=getattr(
                    user, 'state_registration', 'Valor não informado'
                ),
                municipal_registration=getattr(
                    user, 'municipal_registration', 'Valor não informado'
                ),
                cnae_principal=getattr(user, 'cnae_principal', None),
                crt=getattr(user, 'crt', None),
                cep=getattr(user, 'cep', 'Valor não informado'),
                street=getattr(user, 'street', 'Valor não informado'),
                home_number=getattr(user, 'number', 'Valor não informado'),
                complement=getattr(user, 'complement', 'Valor não informado'),
                district=getattr(user, 'district', 'Valor não informado'),
                city=getattr(user, 'city', 'Valor não informado'),
                state=getattr(user, 'state', 'Valor não informado'),
                using_db=conn,
            )

            # 4. Consulta e Cache de dados do CNPJ
            if user.cnpj:
                cnpj_data = await consulting_CNPJ(str(user.cnpj))
                await CNPJCache.create(
                    cnpj=user.cnpj,
                    data_json=json.dumps(cnpj_data, ensure_ascii=False),
                    usuario_id=new_user.id,
                    using_db=conn,
                )

            # 5. Inicialização de Tickets Padrão
            await criar_tickets_padrao(new_user)

            # 6. Criação automática da conta de funcionário para o Admin
            # O PIN padrão para o primeiro acesso ao PDV é '1001'
            default_pin = get_hashed_password('1001')

            admin_employee = await Employees.create(
                nome=new_user.company_name,
                cargo='Manager',
                email=new_user.email,
                senha=default_pin,
                telefone='Não informado',
                ativo=True,
                usuario_id=new_user.id,
                using_db=conn,
            )

            # 7. Inicialização do primeiro Caixa (Checkout)
            checkout_code = await generator_code_to_checkout(new_user.id)

            await Caixa.create(
                nome=f'Caixa Principal - {new_user.company_name}',
                saldo_inicial=0.0,
                saldo_atual=0.0,
                aberto=False,
                caixa_id=checkout_code,
                usuario_id=new_user.id,
                funcionario_id=admin_employee.id,
                valor_total=0.0,
                using_db=conn,
            )

            LOGGER.info(
                f'Empresa {user.company_name} e PDV registrados com sucesso.'
            )

            return {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'company': new_user.company_name,
                'created_at': new_user.criado_em.strftime('%d/%m/%Y %H:%M:%S'),
            }

    except Exception as error:
        LOGGER.error(f'Erro crítico durante o registro: {str(error)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno ao registrar empresa: {str(error)}',
        )
