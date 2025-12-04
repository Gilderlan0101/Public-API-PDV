from typing import List, Optional

from pydantic import BaseModel

# Modelos para o retorno, ajustados conforme seu gerador de relatórios


class ProdutoOut(BaseModel):
    product_code: str
    id: int
    name: str
    sale_price: float
    stock_atual: int
    stock_min: int
    stock_max: int
    date_expired: Optional[str]  # ou datetime, mas serializar para str
    price_uni: float
    lot_bar_code: Optional[int] = None

    class Config:
        orm_mode = True  # Para converter direto do ORM


class EstoqueStatus(BaseModel):
    product_name: str
    current_stock: int
    status: str
    alert: Optional[str] = None


class ProdutoVencido(BaseModel):
    name: str
    expired_date: str
    stock: int
    price: float
    valor_lote: float
    dias_restantes: int
    alert: str


class ValidadeInfo(BaseModel):
    produtos_vencendo: List[ProdutoVencido]
    produtos_vencidos: List[ProdutoVencido]
    valor_total_vencido: float
    valor_total_potencial: float


class RelatorioOut(BaseModel):
    estoque: List[EstoqueStatus]
    validade: ValidadeInfo


class ResponseOut(BaseModel):
    products: List[ProdutoOut]
    aviso: RelatorioOut
