from typing import List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    HttpUrl,
    model_validator,
)

from src.schemas.fornecedor.schemas_fornecedor import (
    Address,
    BankAccount,
    CNPJType,
    ContactPerson,
    CPFType,
    IEStatus,
    IEType,
    PaymentTerm,
    Phone,
    SupplierBase,
    SupplierStatus,
    SupplierType,
    TaxRegime,
)


class SupplierUpdate(BaseModel):
    """Schema para atualização de fornecedor, todos os campos opcionais"""

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        from_attributes=True,
        str_strip_whitespace=True,
    )

    # Identificação
    tipo: Optional[SupplierType] = None
    razao_social: Optional[str] = Field(None, max_length=200)
    nome_fantasia: Optional[str] = Field(None, max_length=200)

    # Documentos
    cnpj: Optional[CNPJType] = None
    cpf: Optional[CPFType] = None
    ie_status: Optional[IEStatus] = None
    inscricao_estadual: Optional[IEType] = None
    inscricao_municipal: Optional[str] = Field(None, max_length=20)

    # Fiscal
    regime_tributario: Optional[TaxRegime] = None

    # Contatos
    email: Optional[EmailStr] = None
    telefones: Optional[List[Phone]] = None
    site: Optional[HttpUrl] = None
    contato_principal: Optional[ContactPerson] = None
    contatos_secundarios: Optional[List[ContactPerson]] = None

    # Endereço
    endereco: Optional[Address] = None

    # Financeiro
    prazo_pagamento: Optional[PaymentTerm] = None
    prazo_personalizado_dias: Optional[int] = Field(None, ge=1, le=365)
    limite_credito: Optional[float] = Field(None, ge=0)
    desconto_padrao_percent: Optional[float] = Field(None, ge=0, le=100)

    # Bancário
    contas_bancarias: Optional[List[BankAccount]] = None

    # Operacional
    categorias_fornecimento: Optional[List[str]] = None
    observacoes: Optional[str] = Field(None, max_length=2000)
    status: Optional[SupplierStatus] = None

    @model_validator(mode='after')
    def validate_documents(self) -> 'SupplierUpdate':
        """Validação cruzada entre tipo de pessoa e documentos"""
        if self.tipo == SupplierType.PESSOA_JURIDICA:
            if self.cnpj is None and self.cpf is not None:
                raise ValueError('CNPJ deve ser informado para PJ')
        elif self.tipo == SupplierType.PESSOA_FISICA:
            if self.cpf is None and self.cnpj is not None:
                raise ValueError('CPF deve ser informado para PF')
        return self

    @model_validator(mode='after')
    def validate_payment_terms(self) -> 'SupplierUpdate':
        """Validação do prazo personalizado"""
        if self.prazo_pagamento == PaymentTerm.PERSONALIZADO:
            if self.prazo_personalizado_dias is None:
                raise ValueError(
                    'prazo_personalizado_dias é obrigatório quando prazo_pagamento é Personalizado'
                )
        elif self.prazo_personalizado_dias is not None:
            raise ValueError(
                'prazo_personalizado_dias só deve ser informado quando prazo_pagamento é Personalizado'
            )
        return self
