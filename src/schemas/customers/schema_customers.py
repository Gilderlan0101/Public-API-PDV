import re
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, confloat, field_validator
from pydantic_br import CEP, CPF


# ------------------------------
# Enum de status do cliente
# ------------------------------
class Status(Enum):
    """Status do cliente: ATIVO, PENDENTE, ATRASO. Relacionado a fatura"""

    ATIVO = 'ATIVO'
    PENDENTE = 'PENDENTE'
    ATRASO = 'ATRASO'


# ------------------------------
# Schema para cadastro de clientes
# ------------------------------
class SchemasCustomer(BaseModel):
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description='Nome completo do cliente',
    )
    birth_date: datetime
    cpf: CPF
    mother_name: Optional[str] = Field(None, max_length=150)
    road: str = Field(..., max_length=150)
    house_number: str  # pode incluir complemento
    neighborhood: str = Field(..., max_length=100)
    city: str = Field(..., max_length=100)
    tel: str
    cep: CEP
    credit: confloat(ge=0)
    # se não passar, backend preenche com credit
    current_balance: Optional[confloat(ge=0)] = None
    due_date: datetime
    status: Status

    # Validação de datas
    @field_validator('birth_date', 'due_date', mode='before')
    def parse_date(cls, v):
        if isinstance(v, str):
            if '/' in v:
                day, month, year = map(int, v.split('/'))
                if year < 100:
                    year += 2000 if year <= 30 else 1900
                return datetime(year, month, day)
            elif '-' in v and len(v) == 10:
                return datetime.strptime(v, '%Y-%m-%d')
        return v

    # Validação de telefone
    @field_validator('tel')
    def validate_tel(cls, v):
        digits = re.sub(r'\D', '', v)
        if len(digits) not in [10, 11]:
            raise ValueError(
                'Telefone inválido. Deve ter 10 ou 11 dígitos (com DDD).'
            )
        return (
            f'({digits[0:2]}) {digits[2:7]}-{digits[7:]}'
            if len(digits) == 11
            else f'({digits[0:2]}) {digits[2:6]}-{digits[6:]}'
        )

    # Exibição em formato brasileiro
    def model_dump_br(self):
        data = self.model_dump()
        data['birth_date'] = data['birth_date'].strftime('%d/%m/%Y')
        data['due_date'] = data['due_date'].strftime('%d/%m/%Y')
        data['credit'] = (
            f"R$ {data['credit']:,.2f}".replace(',', 'X')
            .replace('.', ',')
            .replace('X', '.')
        )
        data['current_balance'] = (
            f"R$ {data['current_balance']:,.2f}".replace(',', 'X')
            .replace('.', ',')
            .replace('X', '.')
        )
        return data

    class Config:
        json_encoders = {datetime: lambda v: v.strftime('%d/%m/%Y')}


# ------------------------------
# Schema para listar clientes / exibir cliente
# ------------------------------
class GetCustomers(BaseModel):
    id: int
    full_name: str
    cpf: str
    credit: float
    current_balance: float
    total_spent: float
    tel: str
    due_date: datetime
    status: str

    class Config:
        from_attributes = True

    def model_dump_br(self):
        data = self.model_dump()
        data['credit'] = (
            f"R$ {data['credit']:,.2f}".replace(',', 'X')
            .replace('.', ',')
            .replace('X', '.')
        )
        data['current_balance'] = (
            f"R$ {data['current_balance']:,.2f}".replace(',', 'X')
            .replace('.', ',')
            .replace('X', '.')
        )
        data['total_spent'] = (
            f"R$ {data['total_spent']:,.2f}".replace(',', 'X')
            .replace('.', ',')
            .replace('X', '.')
        )
        data['due_date'] = data['due_date'].strftime('%d/%m/%Y')
        return data


# ------------------------------
# Schema para atualização de crédito/gasto
# ------------------------------
class SchemasCustomerCreditUpdate(BaseModel):
    current_balance: confloat(ge=0.0)  # saldo atual >= 0

    @field_validator('current_balance')
    def validate_balance(cls, v):
        if v < 0:
            raise ValueError('Saldo não pode ser negativo')
        return v
