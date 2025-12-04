from datetime import datetime
from typing import List, Optional
from zoneinfo import ZoneInfo

from tortoise import fields, models

from src.model.sale import Sales


class Customer(models.Model):
    """
    Modelo de Clientes vinculados a um usuário (empresa) e com relacionamento com vendas.
    """

    id = fields.IntField(pk=True)

    # Dados pessoais
    full_name = fields.CharField(max_length=150)
    birth_date = fields.DatetimeField()
    cpf = fields.CharField(max_length=14, unique=True, index=True)
    mother_name = fields.CharField(max_length=150, null=True)

    # Endereço
    road = fields.CharField(max_length=150)
    house_number = fields.CharField(max_length=10)  # número + complemento
    neighborhood = fields.CharField(max_length=100)
    city = fields.CharField(max_length=100)
    tel = fields.CharField(max_length=20)  # DDD + 9 dígitos
    cep = fields.CharField(max_length=10)

    # Financeiro
    credit = fields.FloatField()
    current_balance = fields.FloatField(default=0)
    total_spent = fields.FloatField(default=0)
    due_date = fields.DatetimeField()
    status = fields.CharField(max_length=20, default='ativo')

    # Auditoria
    created_at = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )
    updated_at = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )

    # 🔹 Relacionamento com usuário
    usuario = fields.ForeignKeyField(
        'models.Usuario', related_name='customers', on_delete=fields.CASCADE
    )

    # 🔹 Relacionamento com vendas
    vendas: fields.ReverseRelation['Sales']
