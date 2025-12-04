import json

from fastapi import APIRouter, HTTPException, status
from tortoise.transactions import in_transaction

from src.model.caixa import Caixa
from src.model.employee import Employees
from src.utils.sales_code_generator import generator_code_to_checkout

from ..auth.auth_jwt import get_hashed_password
from ..model.tickets import criar_tickets_padrao
from ..model.user import CNPJCache, Usuario
from ..schemas.schema_user import CompanyRegisterSchema
from ..services.consulting_cnpj import consulting_CNPJ

registerRT = APIRouter(tags=['Autenticação'])


@registerRT.post('/cadastro', status_code=status.HTTP_201_CREATED)
async def register(user: CompanyRegisterSchema):
    # Verifica se o email já existe
    existing_user = await Usuario.filter(email=user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail='Email já cadastrado.')

    # Criptografa a senha
    hashed_password = get_hashed_password(user.pwd)

    # Cria o usuário
    new_user = Usuario(
        username=user.full_name,
        email=user.email,
        password=hashed_password,
        company_name=user.company_name,
        trade_name=getattr(user, 'trade_name', None),
        membros=getattr(user, 'membros', 0),
        cpf=user.cpf,
        cnpj=user.cnpj,
        state_registration=getattr(user, 'state_registration', None),
        municipal_registration=getattr(user, 'municipal_registration', None),
        cnae_principal=getattr(user, 'cnae_principal', None),
        crt=getattr(user, 'crt', None),
        cep=getattr(user, 'cep', None),
        street=getattr(user, 'street', None),
        number=getattr(user, 'number', None),
        complement=getattr(user, 'complement', None),
        district=getattr(user, 'district', None),
        city=getattr(user, 'city', None),
        state=getattr(user, 'state', None),
    )

    # Criando tickts padrão

    async with in_transaction() as conn:
        await new_user.save(using_db=conn)

        # Busca dados do CNPJ e salva no cache
        if user.cnpj:
            searching_for_data = await consulting_CNPJ(str(user.cnpj))
            full_data = CNPJCache(
                cnpj=user.cnpj,
                data_json=json.dumps(searching_for_data, ensure_ascii=False),
                usuario_id=new_user.id,
            )
            await full_data.save(using_db=conn)
    await criar_tickets_padrao(new_user)  # Este aquivo precisa de refaruração

    # Criando um caixa para empresa ao cadastra uma empresa
    # Todas as empresa devem posuir um caixa aasim como os funcionarios

    hashed_password = get_hashed_password('1001')
    try:

        # Cria uma conta como funcionario
        admin_is_employe = await Employees.create(
            nome=new_user.company_name,
            cargo='Caixa',
            email=new_user.email,
            senha=hashed_password,
            telefone='Não informado',
            ativo=True,
            usuario_id=new_user.id,
        )

        checkout_id = await generator_code_to_checkout(new_user.id)

        checkout_admin = await Caixa.create(
            nome=f'Caixa - {new_user.company_name}',
            saldo_inicial=0.0,
            saldo_atual=0.0,
            aberto=False,
            caixa_id=checkout_id,
            usuario_id=new_user.id,
            funcionario_id=admin_is_employe.id,
            valor_total=0.0,
        )

    except Exception as e:
        raise e

    # Retorno seguro (sem senha)
    return {
        'id': new_user.id,
        'username': new_user.username,
        'email': new_user.email,
        'empresa': new_user.company_name,
        'criado_em': new_user.criado_em.strftime('%d/%m/%Y %H:%M:%S'),
    }
