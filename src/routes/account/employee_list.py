import http
from typing import List

from fastapi import Depends, HTTPException

from src.auth.deps import get_current_user
from src.controllers.employees.get_employee import getEmployees
from src.model.user import Usuario
from src.schemas.funcs.registre_funcs import OutputFormat

from .account import employees_router


@employees_router.get('/employee_list', response_model=List[OutputFormat])
async def alluserEmployee(
    current_user: Usuario = Depends(get_current_user, use_cache=True)
):
    """
    Retorna todos os funcionários do usuário atual
    """

    if not current_user.id:
        raise HTTPException(status_code=404, detail='Usuário não encontrado')

    # CORREÇÃO: Adicionar await para a função assíncrona
    employee = await getEmployees(current_user.id)

    # Verifica se employee é None ou lista vazia
    if not employee:
        raise HTTPException(
            status_code=404,
            detail='Nenhum funcionário encontrado para este usuário',
        )

    return employee
