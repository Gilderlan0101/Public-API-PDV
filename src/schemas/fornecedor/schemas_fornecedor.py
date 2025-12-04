from __future__ import annotations

import re
from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    constr,
    field_validator,
    model_validator,
)


# =========================
# Enums
# =========================
class SupplierType(str, Enum):
    PESSOA_JURIDICA = 'PJ'
    PESSOA_FISICA = 'PF'


class TaxRegime(str, Enum):
    SIMPLES_NACIONAL = 'Simples Nacional'
    LUCRO_PRESUMIDO = 'Lucro Presumido'
    LUCRO_REAL = 'Lucro Real'
    MEI = 'MEI'
    OUTRO = 'Outro'


class IEStatus(str, Enum):
    CONTRIBUINTE = 'Contribuinte'
    ISENTO = 'Isento'
    NAO_CONTRIBUINTE = 'Não Contribuinte'


class PaymentTerm(str, Enum):
    AVISTA = 'À vista'
    DIAS_7 = '7 dias'
    DIAS_14 = '14 dias'
    DIAS_21 = '21 dias'
    DIAS_28 = '28 dias'
    DIAS_30 = '30 dias'
    DIAS_45 = '45 dias'
    DIAS_60 = '60 dias'
    PERSONALIZADO = 'Personalizado'


class SupplierStatus(str, Enum):
    ATIVO = 'Ativo'
    INATIVO = 'Inativo'
    BLOQUEADO = 'Bloqueado'
    PENDENTE = 'Pendente'


class BankAccountType(str, Enum):
    CORRENTE = 'corrente'
    POUPANCA = 'poupança'
    SALARIO = 'salário'


# =========================
# Type Aliases para melhor legibilidade
# =========================
DDDType = constr(pattern=r'^\d{2}$')
PhoneNumberType = constr(pattern=r'^\d{8,9}$')
CepType = constr(pattern=r'^\d{5}-?\d{3}$')
UFType = constr(pattern=r'^[A-Z]{2}$')
BankCodeType = constr(pattern=r'^\d{3}$')
AgencyType = constr(pattern=r'^\d{1,6}(-\d)?$')
AccountType = constr(pattern=r'^\d{1,12}(-\d{1})?$')
DigitType = constr(pattern=r'^\d{0,2}$')
DocumentType = constr(min_length=11, max_length=18)
CNPJType = constr(pattern=r'^\d{14}$')
CPFType = constr(pattern=r'^\d{11}$')
IEType = constr(strip_whitespace=True, min_length=2, max_length=20)


# =========================
# Objetos de apoio
# =========================
class Phone(BaseModel):
    ddd: DDDType = Field(..., description='DDD com 2 dígitos')
    numero: PhoneNumberType = Field(
        ..., description='Número sem DDD, 8 ou 9 dígitos'
    )
    whatsapp: bool = False
    principal: bool = False

    model_config = ConfigDict(from_attributes=True)


class Address(BaseModel):
    cep: CepType = Field(..., example='01311-000')
    logradouro: str = Field(..., max_length=200)
    numero: str = Field(..., max_length=20)
    complemento: Optional[str] = Field(None, max_length=100)
    bairro: str = Field(..., max_length=100)
    cidade: str = Field(..., max_length=100)
    uf: UFType = Field(..., example='SP')
    referencia: Optional[str] = Field(None, max_length=200)

    model_config = ConfigDict(from_attributes=True)


class ContactPerson(BaseModel):
    nome: str = Field(..., max_length=100)
    email: Optional[EmailStr] = None
    telefone: Optional[Phone] = None
    cargo: Optional[str] = Field(None, max_length=50)
    departamento: Optional[str] = Field(None, max_length=50)
    observacoes: Optional[str] = Field(None, max_length=500)

    model_config = ConfigDict(from_attributes=True)


class BankAccount(BaseModel):
    banco: constr(min_length=3, max_length=50) = Field(..., example='Itaú')
    codigo_banco: BankCodeType = Field(..., example='341')
    agencia: AgencyType = Field(..., example='1234')
    digito_agencia: Optional[DigitType] = None
    conta: AccountType = Field(..., example='123456-7')
    digito_conta: DigitType = Field(..., example='1')
    tipo: BankAccountType = BankAccountType.CORRENTE
    titular: str = Field(..., max_length=100)
    documento_titular: DocumentType = Field(
        ..., description='CPF/CNPJ do titular'
    )
    pix: Optional[str] = Field(None, max_length=140, description='Chave PIX')

    model_config = ConfigDict(from_attributes=True)


# =========================
# Schema principal
# =========================
class SupplierBase(BaseModel):
    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )

    # Identificação
    tipo: SupplierType = SupplierType.PESSOA_JURIDICA
    razao_social: str = Field(..., max_length=200)
    nome_fantasia: Optional[str] = Field(
        None, max_length=200, description='Apelido comercial'
    )

    # Documentos
    cnpj: Optional[CNPJType] = Field(
        None, description='Apenas números; para PJ'
    )
    cpf: Optional[CPFType] = Field(None, description='Apenas números; para PF')
    ie_status: IEStatus = IEStatus.CONTRIBUINTE
    inscricao_estadual: Optional[IEType] = None
    inscricao_municipal: Optional[str] = Field(None, max_length=20)

    # Fiscal
    regime_tributario: Optional[TaxRegime] = TaxRegime.SIMPLES_NACIONAL

    # Contatos
    email: Optional[EmailStr] = None
    telefones: List[Phone] = Field(default_factory=list)
    site: Optional[HttpUrl] = None
    contato_principal: Optional[ContactPerson] = None
    contatos_secundarios: List[ContactPerson] = Field(default_factory=list)

    # Endereço
    endereco: Address

    # Financeiro
    prazo_pagamento: PaymentTerm = PaymentTerm.DIAS_30
    prazo_personalizado_dias: Optional[int] = Field(
        None,
        ge=1,
        le=365,
        description='Obrigatório se PaymentTerm = PERSONALIZADO',
    )
    limite_credito: Optional[float] = Field(0, ge=0)
    desconto_padrao_percent: float = Field(0, ge=0, le=100)

    # Bancário - CORREÇÃO AQUI: mudado para List[BankAccount]
    contas_bancarias: List[BankAccount] = Field(default_factory=list)

    # Operacional
    categorias_fornecimento: List[str] = Field(
        default_factory=list,
        description='Ex.: bebidas, laticínios, matérias-primas',
    )
    observacoes: Optional[str] = Field(None, max_length=2000)
    status: SupplierStatus = SupplierStatus.ATIVO

    @model_validator(mode='after')
    def validate_documents(self) -> 'SupplierBase':
        """Validação cruzada entre tipo de pessoa e documentos"""
        if self.tipo == SupplierType.PESSOA_JURIDICA:
            if not self.cnpj:
                raise ValueError('CNPJ é obrigatório para PJ')
            if self.cpf:
                raise ValueError('CPF não deve ser informado para PJ')
        elif self.tipo == SupplierType.PESSOA_FISICA:
            if not self.cpf:
                raise ValueError('CPF é obrigatório para PF')
            if self.cnpj:
                raise ValueError('CNPJ não deve ser informado para PF')

        return self

    @model_validator(mode='after')
    def validate_payment_terms(self) -> 'SupplierBase':
        """Validação do prazo personalizado"""
        if self.prazo_pagamento == PaymentTerm.PERSONALIZADO:
            if self.prazo_personalizado_dias is None:
                raise ValueError(
                    'prazo_personalizado_dias é obrigatório quando '
                    'prazo_pagamento é Personalizado'
                )
        elif self.prazo_personalizado_dias is not None:
            raise ValueError(
                'prazo_personalizado_dias só deve ser informado quando '
                'prazo_pagamento é Personalizado'
            )

        return self


class SupplierCreate(SupplierBase):
    """Schema para criação de fornecedor"""

    pass


class SupplierUpdate(SupplierBase):
    """Schema para atualização de fornecedor"""

    pass


class Supplier(SupplierBase):
    """Schema completo com campos de auditoria"""

    id: int = Field(..., description='ID único gerado pelo sistema')
    criado_em: datetime = Field(default_factory=datetime.now)
    atualizado_em: datetime = Field(default_factory=datetime.now)
    ativo_desde: Optional[date] = None
    criado_por: Optional[str] = Field(
        None, description='Usuário que criou o registro'
    )
    atualizado_por: Optional[str] = Field(
        None, description='Usuário que atualizou o registro'
    )


class SupplierSummary(BaseModel):
    """Schema resumido para listagens"""

    id: int
    razao_social: str
    nome_fantasia: Optional[str] = None
    cnpj: Optional[str] = None
    cpf: Optional[str] = None
    email: Optional[str] = None
    status: SupplierStatus
    cidade: str
    uf: str

    model_config = ConfigDict(from_attributes=True)


# =========================
# Schemas de resposta
# =========================
class SupplierResponse(BaseModel):
    """Resposta padrão para APIs"""

    success: bool
    message: str
    data: Optional[Supplier] = None
    errors: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class SupplierListResponse(BaseModel):
    """Resposta para listagens"""

    success: bool
    total: int
    page: int
    pages: int
    data: List[SupplierSummary]

    model_config = ConfigDict(from_attributes=True)


# =========================
# Utilitários
# =========================
def format_cnpj(cnpj: str) -> str:
    """Formata CNPJ para exibição: XX.XXX.XXX/XXXX-XX"""
    if len(cnpj) != 14:
        return cnpj
    return f'{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}'


def format_cpf(cpf: str) -> str:
    """Formata CPF para exibição: XXX.XXX.XXX-XX"""
    if len(cpf) != 11:
        return cpf
    return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


def sanitize_document(document: str) -> str:
    """Remove formatação de documentos (pontos, traços, barras)"""
    return re.sub(r'[\.\/-]', '', document) if document else document
