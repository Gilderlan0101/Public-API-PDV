from fastapi import APIRouter, Body, Depends, HTTPException, status

from src.auth.deps import get_current_user
from src.model.caixa import Caixa  # ← IMPORTE O MODELO DO CAIXA
from src.model.employee import Employees
from src.model.user import Usuario
from src.routes.registre import get_hashed_password
from src.schemas.funcs.registre_funcs import EmployeesCreate
from src.utils.sales_code_generator import generator_code_to_checkout

employees_router = APIRouter(prefix='/auth', tags=['Autenticação'])

# Tamananho da senha que o funcionario deve conte
PASSWORD_LENGTH = 4


@employees_router.post('/funcs')
async def create_employees(
    func_data: EmployeesCreate = Body(...),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Cadastra um novo funcionário.
    Se o cargo for "Caixa", cria automaticamente um caixa para o funcionário.

    Args:
        func_data (EmployeesCreate): Dados do funcionário.
        current_user: (Usuario): Usuário autenticado que está criando um funcionário.

    Raises:
        HTTPException: Se não estive autenticado, email já cadastrado ou seha inválida.

    Returns:
        dict: Mensagem de sucesso e dados do funcionário criado.
    """

    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Usuário não autenticado',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    # Verificando se esse email já existe
    existing = await Employees.filter(email=func_data.email).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email já cadastrado.',
        )

    # Valida senha de 4 dígitos
    if len(str(func_data.senha)) != PASSWORD_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Senha deve ter {PASSWORD_LENGTH} dígitos.',
        )

    # Criando Hash da senha
    hashed_password = get_hashed_password(func_data.senha)

    # Cria funcionário
    new_func = await Employees.create(
        nome=func_data.nome,
        cargo=func_data.cargo,
        email=func_data.email,
        senha=hashed_password,
        telefone=func_data.telefone,
        ativo=True,
        usuario_id=current_user.id,
    )

    # ✅ SE O CARGO FOR "CAIXA", CRIA AUTOMATICAMENTE UM CAIXA
    if func_data.cargo.lower() == 'caixa':
        await create_caixa_for_employee(new_func, current_user.id)

    return {
        'msg': 'Funcionário cadastrado com sucesso',
        'funcionario': {
            'id': new_func.id,
            'nome': new_func.nome,
            'cargo': new_func.cargo,
            'email': new_func.email,
            'telefone': new_func.telefone,
            'ativo': new_func.ativo,
            'usuario_id': new_func.usuario_id,
        },
    }


async def create_caixa_for_employee(funcionario: Employees, usuario_id: int):
    """
    Cria automaticamente um caixa para um funcionário com cargo "Caixa"
    """
    try:
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

        print(
            f'✅ Caixa criado automaticamente para {funcionario.nome}: ID {caixa_id}'
        )
        return novo_caixa

    except Exception as e:
        print(f'❌ Erro ao criar caixa para {funcionario.nome}: {e}')
        # Não levanta exceção para não quebrar o cadastro do funcionário
        return None
