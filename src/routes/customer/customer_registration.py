from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.deps import SystemUser, get_current_user
from src.model.customers import Customer, ZoneInfo
from src.model.employee import Employees
from src.schemas.customers.schema_customers import (
    GetCustomers,
    SchemasCustomer,
    SchemasCustomerCreditUpdate,
)

customers = APIRouter(tags=['Customers'])


# ===============================
# Criar cliente
# ===============================
@customers.post('/create-customer')
async def create_customer(
    form: SchemasCustomer,
    current_user: SystemUser = Depends(get_current_user),
):
    # Verifica se já existe cliente com o mesmo CPF
    if await Customer.filter(cpf=form.cpf).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='⚠️ Cliente já cadastrado com este CPF.',
        )

    # Preenche current_balance com credit caso não seja informado
    current_balance = getattr(form, 'current_balance', None) or form.credit

    # Cria o cliente
    customer = await Customer.create(
        full_name=form.full_name,
        birth_date=form.birth_date,
        cpf=form.cpf,
        mother_name=form.mother_name,
        road=form.road,
        house_number=form.house_number,
        neighborhood=form.neighborhood,
        city=form.city,
        tel=form.tel,
        cep=form.cep,
        credit=form.credit,
        current_balance=current_balance,
        total_spent=0,
        due_date=form.due_date,
        status=form.status.value,
        usuario_id=current_user.empresa_id,
    )

    # Converte para dict compatível com Pydantic
    customer_data = {
        'full_name': customer.full_name,
        'birth_date': customer.birth_date,
        'cpf': customer.cpf,
        'mother_name': customer.mother_name,
        'road': customer.road,
        'house_number': customer.house_number,
        'neighborhood': customer.neighborhood,
        'city': customer.city,
        'tel': customer.tel,
        'cep': customer.cep,
        'credit': customer.credit,
        'current_balance': customer.current_balance,
        'due_date': customer.due_date,
        'status': customer.status,
    }

    return {
        'message': '✅ Cliente cadastrado com sucesso!',
        'customer': SchemasCustomer.model_validate(
            customer_data
        ).model_dump_br(),
    }


@customers.get('/list-customer', response_model=List[GetCustomers])
async def list_customer(current_user: SystemUser = Depends(get_current_user)):
    """
    Lista clientes do usuário atual.
    CORREÇÃO: Cada usuário (admin ou funcionário) deve ver apenas SEUS PRÓPRIOS clientes
    """
    try:

        # CORREÇÃO: Sempre busca clientes do usuário atual, independente de ser admin ou funcionário

        clients = await Customer.filter(
            usuario_id=current_user.empresa_id
        ).all()

        return clients

    except Exception as e:
        print(f'❌ Erro ao listar clientes: {e}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao buscar clientes',
        )


# ===============================
# Atualizar crédito/gasto do cliente
# ===============================
@customers.put('/update-customer-credit')
async def update_customer_credit(
    update_data: SchemasCustomerCreditUpdate,
    cpf: str = Query(..., description='CPF do cliente'),
    current_user: SystemUser = Depends(get_current_user),
):
    customer = await Customer.filter(
        cpf=cpf, usuario_id=current_user.empresa_id
    ).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Cliente não encontrado pelo CPF',
        )

    if update_data.current_balance > customer.credit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Gasto acumulado (R$ {update_data.current_balance:,.2f}) excede o crédito total (R$ {customer.credit:,.2f})',
        )

    customer.current_balance = update_data.current_balance
    customer.total_spent = customer.credit - customer.current_balance
    customer.updated_at = datetime.now(ZoneInfo('America/Sao_Paulo'))
    await customer.save()

    return GetCustomers(
        id=customer.id,
        full_name=customer.full_name,
        cpf=customer.cpf,
        credit=customer.credit,
        current_balance=customer.current_balance,
        total_spent=customer.total_spent,
        due_date=customer.due_date,
        status=customer.status,
    )


# ===============================
# Deletar cliente
# ===============================
@customers.delete('/delete-customer/{customer_id}')
async def delete_customer(
    customer_id: int,
    current_user: SystemUser = Depends(get_current_user),
):
    customer = await Customer.filter(
        id=customer_id, usuario_id=current_user.empresa_id
    ).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Cliente não encontrado',
        )

    await customer.delete()
    return {'message': '✅ Cliente excluído com sucesso!'}
