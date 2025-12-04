from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.deps import SystemUser, get_current_user
from src.controllers.employees.edit_employee import EmployeeUpdater
from src.model.employee import Employees
from src.model.user import Usuario
from src.schemas.funcs.registre_funcs import UpdateEmployee

# 🔹 Definindo o router
employees_router = APIRouter()


@employees_router.delete(
    '/delete_employee',
    status_code=status.HTTP_200_OK,
    summary='Excluir um funcionário por ID',
)
async def delete_employee(
    id_employee: int = Query(
        ..., description='ID do funcionário a ser excluído'
    ),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Exclui um registro de funcionário com base no ID fornecido.

    Requer que o usuário esteja autenticado.

    Raises:
        HTTPException 404: Se o funcionário não for encontrado.
        HTTPException 403: Se o usuário logado não tiver permissão.
    """

    # 1. (Opcional) Verificação de Autorização
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Apenas administradores podem excluir funcionários."
    #     )

    # 2. Buscar funcionário pertencente ao usuário logado
    employee = await Employees.get_or_none(
        id=id_employee, usuario_id=current_user.id
    )

    if not employee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Funcionário com ID {id_employee} não encontrado.',
        )

    # 3. Deletar funcionário
    await employee.delete()

    # 4. Retorno
    return {
        'message': f'Funcionário com ID {id_employee} excluído com sucesso.',
        'deleted_id': id_employee,
    }


@employees_router.put(
    '/atualiza-funcionario',
    status_code=status.HTTP_200_OK,
    summary='Atualizar dados de um funcionário',
)
async def update_data_employee(
    employee: UpdateEmployee,
    current_user: SystemUser = Depends(get_current_user),
):
    """
    Atualiza dados de um funcionário (senha e/ou username).
    Requer autenticação.
    """

    update_in = EmployeeUpdater(
        user_id=current_user.id,
        email=employee.email,
        password=employee.password,
        username=employee.username,
    )

    # Executa atualização
    return await update_in.handle_update_request()
