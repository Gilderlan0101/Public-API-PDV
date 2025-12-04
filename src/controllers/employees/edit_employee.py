from typing import Any, Dict, Optional

import tortoise.exceptions
from fastapi import HTTPException, status

from src.auth.auth_jwt import get_hashed_password
from src.model.employee import (  # Assumindo que Employees é seu modelo Tortoise ORM
    Employees,
)


class EmployeeUpdater:
    """
    Classe responsável por preparar e executar a atualização de dados do funcionário.
    """

    def __init__(
        self,
        user_id: int,
        email: str,
        password: Optional[str] = None,
        username: Optional[str] = None,
    ):
        # Validação inicial dos dados a serem atualizados
        if not (password or username):
            raise ValueError(
                "Pelo menos 'password' ou 'username' deve ser fornecido para a atualização."
            )

        self.user_id = user_id
        self.email = email
        self.password = password
        self.username = username
        self.updates: Dict[str, Any] = {}

        # Prepara o dicionário de atualizações (só inclui se o valor foi fornecido)
        if self.password not in (None, ''):
            self.updates['senha'] = get_hashed_password(self.password)

        # username: nome do funcionario'
        if self.username not in (None, ''):
            self.updates['nome'] = self.username

    async def update_employee_data(self, extra_updates: Dict[str, Any] = None):
        """
        Executa a atualização dos dados do funcionário de forma performática
        usando o método update() direto na query do Tortoise.

        Retorna o número de registros afetados (0 ou 1).
        """
        updates = {**self.updates, **(extra_updates or {})}

        if not self.updates:
            # Não deve ocorrer se o construtor for usado corretamente, mas é uma garantia
            return 0

        # Filtra o registro e aplica as atualizações preparadas de uma vez
        updated_count = await Employees.filter(
            usuario_id=self.user_id, email=self.email
        ).update(**updates)
        return updated_count

    async def handle_update_request(self) -> dict:
        """
        Executa a atualização e lida com a resposta/exceção HTTP.
        """
        if not self.updates:
            # Caso não tenha dados para atualizar
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Nenhum dado (senha ou nome de usuário) fornecido para atualização.',
            )

        # 1. Tenta executar a atualização
        try:
            updated_count = await self.update_employee_data()
        except tortoise.exceptions.DBAPIError as e:
            # Captura erros de banco de dados (ex: violação de unique constraint)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Erro no banco de dados durante a atualização: {e}',
            )

        # 2. Verifica o resultado e retorna/lança a exceção
        if updated_count > 0:
            # Gera a mensagem de sucesso dinamicamente
            success_message = 'Funcionário(a) atualizado(a) com sucesso!'
            if self.password and self.username:
                success_message = (
                    'Senha e Nome de usuário atualizados com sucesso.'
                )
            elif self.password:
                success_message = 'Senha atualizada com sucesso.'
            elif self.username:
                success_message = 'Nome de usuário atualizado com sucesso.'

            return {
                'status_code': status.HTTP_200_OK,
                'detail': success_message,
            }
        else:
            # 0 linhas afetadas, geralmente significa que o usuário não foi encontrado
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f'Funcionário(a) com ID {self.user_id} não encontrado(a).',
            )
