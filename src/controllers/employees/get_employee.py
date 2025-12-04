import json
from http.client import HTTPException

import tortoise
import tortoise.exceptions
from fastapi import HTTPException

from src.core.cache import client
from src.model.employee import Employees
from src.schemas.funcs.registre_funcs import OutputFormat


async def getEmployees(user_id: int):
    """GetEmployees Busca todos os fucionarios do usuario admin
    parms: user_id: int | None
    """
    connection = None
    try:
        # Estabelecer conexão explicitamente se necessário
        connection = tortoise.Tortoise.get_connection('default')

        employees = await Employees.filter(usuario_id=user_id).all()
        employee_information = []

        cache_key = f'employee:{user_id}'
        # Verifica se já tem cache
        cache = await client.get(cache_key)
        if cache:
            return json.loads(cache)

        match employees:

            case employees if len(employees) > 0:
                for date in employees:

                    formate_data = OutputFormat(
                        nome=date.nome,
                        valor_venda=date.result_of_all_sales
                        if date.result_of_all_sales is not None
                        else 0,
                        cargo=date.cargo,
                        email=date.email,
                        telefone=date.telefone,
                        user_id=date.id,
                        ativo=date.ativo,
                    )

                    if date.ativo is True:
                        employee_information.append(
                            {
                                'user_id': date.id,
                                'nome': formate_data.nome,
                                'valor_venda': formate_data.valor_venda,
                                'cargo': formate_data.cargo,
                                'email': formate_data.email,
                                'telefone': formate_data.telefone or '',
                                'ativo': formate_data.ativo,
                            }
                        )

                # Salvando obj em cache
                await client.setex(
                    cache_key, 60, json.dumps(employee_information)
                )
                return employee_information

            case _:
                return {
                    'status': False,
                    'message': 'Nemhum fucionario cadastrado',
                }

    except tortoise.exceptions.DoesNotExist:
        raise HTTPException(
            status_code=404,
            detail='Usuario não encontrado. Faça login para prosseguir.',
        )

    except tortoise.exceptions.BaseORMException:
        raise HTTPException(
            status_code=500,
            detail='Estamos enfrentando problemas internos, tente mais tarde ou entre em contato com o suporte.',
        )

    finally:

        try:
            if connection:
                await connection.close()
        except tortoise.exceptions.BaseORMException:
            connection = tortoise.Tortoise.get_connection('default')
            await connection.close()
