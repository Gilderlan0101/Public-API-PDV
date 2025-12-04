from typing import Optional

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


# ========================
# 🔹 Schema Caixa Funcionário
# ========================
class CaixaFuncionarioCreate(SQLModel):
    funcionario_id: int = Field(
        ..., description='ID do funcionário que está abrindo o caixa'
    )
    valor_abertura: float = Field(
        ...,
        description='Valor que o funcionário informou na abertura do caixa',
    )


# ========================
# 🔹 Schema de Atualização do Caixa (Fechamento)
# ========================
class CaixaFuncionarioUpdate(SQLModel):
    caixa_id: int = Field(..., description='ID do caixa a ser fechado')


class AberturaCaixaRequest(BaseModel):
    funcionario_id: int
    saldo_inicial: Optional[float] = 0.0
    nome: Optional[str] = 'Caixa Principal'
