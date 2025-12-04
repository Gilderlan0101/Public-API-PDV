from typing import Optional

from pydantic import BaseModel

from src.auth.deps import SystemUser

# ID_USER =  SystemUser.id


class RegisterUserForPartialMode(BaseModel):
    full_name: str
    cpf: str
    tel: str
    produto: str


class VendaParcialData(BaseModel):
    cpf: str
    valor_recebido: float
    metodo_pagamento: str
    produto: str
    valor_total: float


class AtualizaDividaData(BaseModel):
    cpf: str
    value_received: float
    type_meyhod_payment: str


class InputData(BaseModel):
    product_name: str
    total_price: int
    cpf: str


class PartialDataOutput(BaseModel):
    """Saída de dados ao finalizar uma venda"""

    full_name: str
    value: int
    mensagem: Optional[
        dict
    ]  # ex: {'mensagem': 'O cliente X pagou 30.00 de 100.00 restante 70.00'}


class ReceivePaymentPartial(BaseModel):
    """Receber pagamento do Cliente modo parcial"""

    cpf: str
    value_received: float
    type_meyhod_payment: str
