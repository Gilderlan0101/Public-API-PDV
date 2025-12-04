# Model produtos
from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from tortoise import fields, models

from src.model.sale import Sales


# ========================
# 🔹 Produto
# ========================
class Produto(models.Model):
    id = fields.IntField(pk=True)
    product_code = fields.CharField(max_length=50, index=True)
    name = fields.CharField(max_length=150, index=True)
    stock = fields.IntField(default=0)
    stoke_min = fields.IntField(default=0)
    stoke_max = fields.IntField(default=0)
    date_expired = fields.DatetimeField(null=True)
    fabricator = fields.CharField(max_length=150, null=True)
    cost_price = fields.FloatField()
    price_uni = fields.FloatField()
    sale_price = fields.FloatField()
    supplier = fields.CharField(max_length=150, null=True)
    lot_bar_code = fields.CharField(max_length=100, null=True)
    image_url = fields.CharField(max_length=255, null=True)

    # Campos extras
    product_type = fields.CharField(max_length=100, null=True)
    active = fields.BooleanField(default=True)
    group = fields.CharField(max_length=100, null=True)
    sub_group = fields.CharField(max_length=100, null=True)
    ticket = fields.TextField(null=True, default='Novo')
    sector = fields.CharField(max_length=100, null=True)
    unit = fields.CharField(max_length=20, null=True)
    controllstoke = fields.CharField(max_length=50, null=True)
    sales_config = fields.CharField(max_length=150, null=True)
    detail = fields.TextField(null=True, default='')
    label = fields.TextField(null=True)

    criado_em = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )
    atualizado_em = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )

    # 🔹 Relacionamentos
    usuario = fields.ForeignKeyField(
        'models.Usuario', related_name='produtos', on_delete=fields.CASCADE
    )
    fornecedor = fields.ForeignKeyField(
        'models.Fornecedor',
        related_name='produtos',
        null=True,
        on_delete=fields.SET_NULL,
    )

    vendas: fields.ReverseRelation['Sales']


# ========================
# 🔹 Produto Arquivado
# ========================
class ProdutoArquivado(models.Model):
    id = fields.IntField(pk=True)
    product_code = fields.CharField(max_length=50, index=True)
    name = fields.CharField(max_length=150, index=True)
    stock = fields.IntField(default=0)
    date_expired = fields.DatetimeField(null=True)
    fabricator = fields.CharField(max_length=150, null=True)
    cost_price = fields.FloatField()
    price_uni = fields.FloatField()
    sale_price = fields.FloatField()
    supplier = fields.CharField(max_length=150, null=True)
    lot_bar_code = fields.CharField(max_length=100, null=True)
    image_url = fields.CharField(max_length=255, null=True)

    # Motivo do arquivamento
    description = fields.TextField()

    criado_em = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )
    atualizado_em = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )

    # 🔹 Relacionamentos
    usuario = fields.ForeignKeyField(
        'models.Usuario',
        related_name='produtos_arquivados',
        on_delete=fields.CASCADE,
    )
    produto = fields.ForeignKeyField(
        'models.Produto',
        related_name='arquivados',
        null=True,
        on_delete=fields.SET_NULL,
    )
