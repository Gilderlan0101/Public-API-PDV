from datetime import date, datetime
from enum import Enum
from re import sub as regex_sub
from typing import Annotated, Any, Dict, Optional, Union

from pydantic import BaseModel, Field, HttpUrl, root_validator, validator

# ======================================
# Type Aliases for Validation
# ======================================
Str50 = Annotated[str, Field(min_length=1, max_length=50)]
Str150 = Annotated[str, Field(min_length=2, max_length=150)]
NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]


# ======================================
# Helper Functions for Data Treatment
# ======================================
def remove_special_chars(value: str) -> str:
    """Remove special characters and normalize string"""
    if not value:
        return value
    # Remove accents and special chars
    normalized = regex_sub(r'[^\w\s]', '', value)
    return normalized.strip()


def normalize_boolean_string(value: Union[str, bool, None]) -> str:
    """Normalize boolean-like strings to 'Sim' or 'Não'"""
    if value is None:
        return 'Não'

    if isinstance(value, bool):
        return 'Sim' if value else 'Não'

    if isinstance(value, str):
        value_clean = value.lower().strip()
        true_values = ['sim', 's', 'yes', 'y', 'true', '1', 'ativo', 'active']
        false_values = [
            'nao',
            'não',
            'n',
            'no',
            'false',
            '0',
            'inativo',
            'inactive',
        ]

        if value_clean in true_values:
            return 'Sim'
        elif value_clean in false_values:
            return 'Não'

    return 'Não'


def normalize_product_type(value: Union[str, None]) -> str:
    """Normalize product type string"""
    if not value:
        return 'Comum'

    type_mapping = {
        'comum': 'Comum',
        'fracionado': 'Fracionado',
        'adicional': 'Adicional',
        'valor editavel': 'Valor editável',
        'valor_editavel': 'Valor editável',
        'valor-editavel': 'Valor editável',
        'materia prima': 'Matéria prima',
        'materia_prima': 'Matéria prima',
        'materia-prima': 'Matéria prima',
        'eletronico': 'Eletrônico',
        'eletrônico': 'Eletrônico',
    }

    value_clean = value.lower().strip()
    return type_mapping.get(value_clean, 'Comum')


def normalize_sector(value: Union[str, None]) -> str:
    """Normalize sector string"""
    if not value:
        return 'Fabricação Própria'

    sector_mapping = {
        'fabricacao propria': 'Fabricação Própria',
        'fabricacao_propria': 'Fabricação Própria',
        'fabricação própria': 'Fabricação Própria',
        'local': 'Fabricação Própria',
        'revenda': 'Revenda',
        'terceiros': 'Revenda',
    }

    value_clean = value.lower().strip()
    return sector_mapping.get(value_clean, 'Fabricação Própria')


def normalize_unit(value: Union[str, None]) -> str:
    """Normalize unit of measurement"""
    if not value:
        return 'Unidade'

    unit_mapping = {
        'unidade': 'Unidade',
        'un': 'Unidade',
        'und': 'Unidade',
        'kg': 'Kilograma (kg)',
        'kilograma': 'Kilograma (kg)',
        'g': 'Grama (g)',
        'grama': 'Grama (g)',
        'l': 'Litro (l)',
        'litro': 'Litro (l)',
        'ml': 'Mililitro (ml)',
        'mililitro': 'Mililitro (ml)',
        'cx': 'Caixa',
        'caixa': 'Caixa',
        'pct': 'Pacote',
        'pacote': 'Pacote',
        'fardo': 'Fardo',
    }

    value_clean = value.lower().strip()
    return unit_mapping.get(value_clean, value)


# ======================================
# Product Enums
# ======================================
class ProductGroup(str, Enum):
    BEVERAGES = 'Bebidas'
    FOODS = 'Alimentos'
    FRUITS = 'Frutas'
    VEGETABLES = 'Verduras'
    MEATS = 'Carnes'
    FISH = 'Peixes'
    DAIRY = 'Laticínios'
    BAKERY = 'Padaria'
    SWEETS = 'Doces'
    SNACKS = 'Salgados'
    HYGIENE = 'Higiene'
    CLEANING = 'Limpeza'
    CLOTHES = 'Roupas'
    SHOES = 'Calçados'
    ACCESSORIES = 'Acessórios'
    ELECTRONICS = 'Eletrônicos'
    HOME_APPLIANCES = 'Eletrodomésticos'
    TOOLS = 'Ferramentas'
    SCHOOL_SUPPLIES = 'Material escolar'
    FURNITURE = 'Móveis'
    TOYS = 'Brinquedos'
    GARDENING = 'Jardinagem'
    PETSHOP = 'Petshop'
    OTHERS = 'Outros'


class BeveragesSubGroup(str, Enum):
    REFRIGERANTES = 'Refrigerantes'
    SUCOS = 'Sucos'
    AGUA = 'Água'
    ENERGETICOS = 'Energéticos'
    CERVEJAS = 'Cervejas'
    VINHOS = 'Vinhos'
    CAFE_CHA = 'Café e Chá'


class FoodsSubGroup(str, Enum):
    MASSAS = 'Massas'
    ARROZ_FEIJAO = 'Arroz e Feijão'
    ENLATADOS = 'Enlatados'
    TEMPEROS = 'Temperos e Condimentos'
    CONGELADOS = 'Congelados'


class FruitsSubGroup(str, Enum):
    TROPICAIS = 'Tropicais'
    CITRICAS = 'Cítricas'
    VERMELHAS = 'Frutas Vermelhas'
    SECAS = 'Frutas Secas'


class VegetablesSubGroup(str, Enum):
    FOLHOSAS = 'Folhosas'
    RAIZES = 'Raízes'
    LEGUMES = 'Legumes'
    BROTOS = 'Brotos e Germinados'


class MeatsSubGroup(str, Enum):
    BOVINAS = 'Bovinas'
    SUINAS = 'Suínas'
    AVES = 'Aves'
    EMBUTIDOS = 'Embutidos'


class FishSubGroup(str, Enum):
    FRESCOS = 'Peixes Frescos'
    CONGELADOS = 'Peixes Congelados'
    FRUTOS_DO_MAR = 'Frutos do Mar'


class DairySubGroup(str, Enum):
    LEITES = 'Leites e Bebidas Lácteas'
    QUEIJOS = 'Queijos'
    IOGURTES = 'Iogurtes'
    MANTEIGAS = 'Manteigas e Cremes'


class BakerySubGroup(str, Enum):
    PAES = 'Pães'
    BOLOS = 'Bolos'
    TORTAS = 'Tortas'
    SALGADOS_ASSADOS = 'Salgados Assados'


class SweetsSubGroup(str, Enum):
    CHOCOLATES = 'Chocolates'
    BALAS = 'Balas e Confeitos'
    SORVETES = 'Sorvetes'
    BOLACHAS = 'Bolachas'


class SnacksSubGroup(str, Enum):
    CHIPS = 'Chips'
    PIPOCAS = 'Pipocas'
    SNACKS_SAUDAVEIS = 'Snacks Saudáveis'
    PETISCOS = 'Petiscos'


# ======================================
# Units
# ======================================
class UnitOfMeasurement(str, Enum):
    UNIT = 'Unidade'
    KG = 'Kilograma (kg)'
    GRAM = 'Grama (g)'
    LITER = 'Litro (l)'
    ML = 'Mililitro (ml)'
    MILHEIRO = 'Milheiro'
    CAIXA = 'Caixa'
    PACOTE = 'Pacote'
    PAR = 'Par'
    ROLO = 'Rolo'
    SACO = 'Saco'
    FARDO = 'Fardo'
    BARRA = 'Barra'
    POTE = 'Pote'
    FRASCO = 'Frasco'
    VIDRO = 'Vidro'
    UNIDADE_CAIXA = 'Unidade em Caixa'


# ======================================
# Product Status / Type
# ======================================
class ProductSector(str, Enum):
    LOCAL = 'Fabricação Própria'
    RESALE = 'Revenda'


class ProductStatus(str, Enum):
    YES = 'Sim'
    NO = 'Não'

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            normalized = normalize_boolean_string(value)
            if normalized == 'Sim':
                return cls.YES
            elif normalized == 'Não':
                return cls.NO
        return cls.NO


class ProductType(str, Enum):
    COMMON = 'Comum'
    FRACTIONAL = 'Fracionado'
    ADDITIONAL = 'Adicional'
    EDITABLE_VALUE = 'Valor editável'
    RAW_MATERIAL = 'Matéria prima'
    ELECTRONICS = 'Eletrônico'

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            normalized = normalize_product_type(value)
            for member in cls:
                if member.value == normalized:
                    return member
        return cls.COMMON


class TicketType(str, Enum):
    NEW = 'Novo'
    PROMOTION = 'Promoção'
    COMBO = 'Combo'
    BEST_SELLER = 'Mais Vendido'
    SPECIAL_OFFER = 'Oferta Especial'
    SEASONAL = 'Sazonal'
    LIMITED = 'Edição Limitada'


# ======================================
# Sales Configuration
# ======================================
class ApplyingSalesType(BaseModel):
    discount: Optional[Union[ProductStatus, str, bool]] = None
    rate: Optional[Union[ProductStatus, str, bool]] = None
    balance: Optional[Union[ProductStatus, str, bool]] = None
    valid: Optional[str] = None

    @validator('discount', 'rate', 'balance', pre=True)
    def normalize_sales_config(cls, v):
        if v is None:
            return ProductStatus.NO
        if isinstance(v, bool):
            return ProductStatus.YES if v else ProductStatus.NO
        if isinstance(v, str):
            normalized = normalize_boolean_string(v)
            return (
                ProductStatus.YES if normalized == 'Sim' else ProductStatus.NO
            )
        return v

    class Config:
        use_enum_values = True


# ======================================
# Product Schemas
# ======================================
class ProductRegisterSchema(BaseModel):
    """Schema for registering a new product with data normalization"""

    name: Str150
    product_code: Str50
    stock: NonNegativeInt = 0
    stoke_min: NonNegativeInt = 0
    stoke_max: NonNegativeInt = 0
    date_expired: Optional[datetime] = None
    fabricator: Optional[str] = None
    cost_price: NonNegativeFloat = 0.0
    price_uni: NonNegativeFloat = 0.0
    sale_price: NonNegativeFloat = 0.0
    supplier: Optional[str] = None
    lot_bar_code: Optional[str] = None
    image_url: Optional[str] = None

    product_type: Union[ProductType, str, None] = ProductType.COMMON
    active: Union[ProductStatus, str, bool, None] = ProductStatus.YES
    group: Optional[str] = None
    sub_group: Optional[str] = None
    ticket: Optional[str] = None
    sector: Union[ProductSector, str, None] = ProductSector.LOCAL
    unit: Optional[str] = None
    controllstoke: Union[ProductStatus, str, bool, None] = ProductStatus.YES
    sales_config: Optional[
        Union[ApplyingSalesType, Dict[str, Any], None]
    ] = None

    @root_validator(pre=True)
    def normalize_all_fields(cls, values):
        """Normalize all fields before validation"""

        # Normalize active status
        if 'active' in values:
            values['active'] = normalize_boolean_string(values['active'])

        # Normalize controllstoke
        if 'controllstoke' in values:
            values['controllstoke'] = normalize_boolean_string(
                values['controllstoke']
            )

        # Normalize product_type
        if 'product_type' in values:
            values['product_type'] = normalize_product_type(
                values['product_type']
            )

        # Normalize sector
        if 'sector' in values:
            values['sector'] = normalize_sector(values['sector'])

        # Normalize unit
        if 'unit' in values:
            values['unit'] = normalize_unit(values['unit'])

        # Ensure stock max >= stock min
        if 'stoke_max' in values and 'stoke_min' in values:
            if values['stoke_max'] < values['stoke_min']:
                values['stoke_max'] = values['stoke_min']

        # Ensure sale price >= cost price
        if 'sale_price' in values and 'cost_price' in values:
            if values['sale_price'] < values['cost_price']:
                values['sale_price'] = values['cost_price']

        # Handle sales_config
        if 'sales_config' in values and values['sales_config'] is not None:
            if isinstance(values['sales_config'], dict):
                values['sales_config'] = ApplyingSalesType(
                    **values['sales_config']
                )

        return values

    @validator('name', 'product_code', pre=True)
    def clean_string_fields(cls, v):
        if isinstance(v, str):
            return remove_special_chars(v)
        return v

    @validator('cost_price', 'price_uni', 'sale_price', pre=True)
    def validate_prices(cls, v):
        if isinstance(v, str):
            try:
                # Remove currency symbols and convert
                cleaned = regex_sub(r'[^\d.,-]', '', v)
                cleaned = cleaned.replace(',', '.')
                return float(cleaned)
            except:
                return 0.0
        return v if v is not None else 0.0

    @validator('stock', 'stoke_min', 'stoke_max', pre=True)
    def validate_stock(cls, v):
        if isinstance(v, str):
            try:
                return int(float(v))
            except:
                return 0
        return v if v is not None else 0

    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}


class ProductUpdateSchema(BaseModel):
    """Schema for updating product information"""

    product_code: Optional[str] = None
    name: Optional[str] = None
    stock: Optional[int] = None
    stoke_min: Optional[int] = None
    stoke_max: Optional[int] = None
    date_expired: Optional[date] = None
    fabricator: Optional[str] = None
    cost_price: Optional[float] = None
    price_uni: Optional[float] = None
    sale_price: Optional[float] = None
    supplier: Optional[str] = None
    lot_bar_code: Optional[str] = None
    image_url: Optional[HttpUrl] = None
    description: Optional[str] = None

    product_type: Optional[str] = None
    active: Optional[str] = None
    group: Optional[str] = None
    sub_group: Optional[str] = None
    sector: Optional[str] = None
    unit: Optional[str] = None
    controllstoke: Optional[str] = None
    sales_config: Optional[
        Union[ApplyingSalesType, Dict[str, Any], str]
    ] = None

    @root_validator(pre=True)
    def normalize_update_fields(cls, values):
        """Normalize fields for update"""

        if 'active' in values and values['active'] is not None:
            values['active'] = normalize_boolean_string(values['active'])

        if 'controllstoke' in values and values['controllstoke'] is not None:
            values['controllstoke'] = normalize_boolean_string(
                values['controllstoke']
            )

        if 'product_type' in values and values['product_type'] is not None:
            values['product_type'] = normalize_product_type(
                values['product_type']
            )

        if 'sector' in values and values['sector'] is not None:
            values['sector'] = normalize_sector(values['sector'])

        if 'unit' in values and values['unit'] is not None:
            values['unit'] = normalize_unit(values['unit'])

        if 'sales_config' in values and values['sales_config'] is not None:
            if isinstance(values['sales_config'], dict):
                values['sales_config'] = ApplyingSalesType(
                    **values['sales_config']
                )

        return values

    class Config:
        use_enum_values = True
        extra = 'ignore'


# ======================================
# Response Schema Example
# ======================================
class ProductResponseSchema(ProductRegisterSchema):
    """Schema for product response with ID"""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
