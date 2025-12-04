from typing import Optional

from pydantic import BaseModel, EmailStr, model_validator

"""
Shema_user.py: Onde criamos validações de login e cadastro
do usuario.
"""


class LoginSchema(BaseModel):
    email: EmailStr
    pwd: str


class CompanyRegisterSchema(BaseModel):
    # Dados pessoais
    full_name: str
    cpf: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    pwd: str

    # Dados da empresa
    cnpj: Optional[str] = None
    company_name: str
    trade_name: Optional[str] = None
    state_registration: Optional[str] = None
    municipal_registration: Optional[str] = None
    cnae_principal: Optional[str] = None
    crt: Optional[int] = None  # 1, 2 ou 3

    # Endereço
    cep: Optional[str] = None
    street: Optional[str] = None
    number: Optional[str] = None
    complement: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    # Devemos cria verificaçoes de cpf e cnpj aqui
    def verify_document(self):
        pass

    @model_validator(mode='before')
    def check_cpf_or_cnpj(cls, values):
        if not values.get('cpf') and not values.get('cnpj'):
            raise ValueError('Informe pelo menos CPF ou CNPJ.')
        return values


class TokenSchema(BaseModel):
    id: int
    username: str
    email: EmailStr
    empresa: Optional[str] = None
    empresa_id: Optional[int] = None  #  NOVO CAMPO
    tipo: str
    message: str
    access_token: str
    refresh_token: str
    token_type: str


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None


class SystemUser(BaseModel):
    id: int
    username: str
    email: EmailStr
    company_name: str
    cnpj: Optional[str] = None
    cpf: Optional[str] = None
    is_active: bool = True
    empresa_id: Optional[int] = None  # 🔹 ID real do usuário master/empresa

    model_config = {'from_attributes': True}
