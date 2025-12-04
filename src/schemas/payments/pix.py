from typing import Optional

from pydantic import BaseModel, constr, validator

MIN_NAME_SIZE = 10
MIN_CITY_SIZE = 5


class GenerateQRCodeFor(BaseModel):
    """Schema para criação de PIX"""

    full_name: constr(min_length=MIN_NAME_SIZE, max_length=90)
    city: constr(min_length=MIN_CITY_SIZE, max_length=90)

    value: float
    type_exit: str = 'qr'


# Class responsavel por seleciona uma conta pix. Caso não seja passado um valor
# O codigo usar o primeiro pix que encontra como DEFAULT
class SelectAccount(BaseModel):

    account: Optional[int] = None  # Ou 1
