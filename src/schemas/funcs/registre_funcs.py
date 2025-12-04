from typing import Optional

from pydantic import BaseModel


class EmployeesCreate(BaseModel):
    nome: str
    cargo: str
    email: str
    senha: str
    telefone: str
    ativo: bool


class OutputFormat(BaseModel):
    nome: str
    cargo: str
    email: str
    valor_venda: Optional[int] = None
    telefone: Optional[str] = None
    ativo: bool
    user_id: Optional[int] = None


class UpdateEmployee(BaseModel):

    email: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
