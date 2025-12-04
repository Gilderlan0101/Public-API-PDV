from datetime import datetime
from zoneinfo import ZoneInfo

from tortoise import fields, models


class Partial(models.Model):
    id = fields.IntField(pk=True)

    customers_name = fields.CharField(max_length=150, null=True)
    cpf = fields.CharField(
        max_length=90, null=False, unique=True
    )  # CPF como texto
    tel = fields.CharField(
        max_length=90, null=False, unique=True
    )  # Telefone como texto
    # product_name = fields.TextField(null=True)
    produto = fields.CharField(
        max_length=255, null=True
    )  # Adicione este campo
    value = fields.FloatField(null=True)
    payment_method = fields.CharField(max_length=15, null=True)
    date = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )

    usuario = fields.ForeignKeyField(
        'models.Usuario',
        related_name='partials',
        null=True,
    )


class finished_debts(models.Model):
    id = fields.IntField(pk=True)

    name = fields.CharField(max_length=150, null=True)
    tel = fields.CharField(max_length=90, null=True)
    product_name = fields.TextField(null=True)

    # MUDANÇA CRÍTICA: Adicione CPF para agrupar pagamentos
    cpf = fields.CharField(max_length=14, null=True, index=True)

    # Valor total original da dívida
    original_debt_value = fields.FloatField(null=True)

    # Valor total realmente pago (soma de todos os pagamentos)
    total_paid_value = fields.FloatField(null=True, default=0.0)

    # Histórico de TODOS os pagamentos (array de objetos)
    payment_history = fields.JSONField(null=True, default=list)

    # Status da dívida
    status = fields.CharField(
        max_length=20, default='quitada'
    )  # quitada, parcial

    date = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )

    usuario = fields.ForeignKeyField(
        'models.Usuario',
        related_name='partials_finished_debts',
        null=True,
    )

    class Meta:
        table = 'finished_debts'
        indexes = [
            ('cpf', 'usuario_id'),
            ('status',),
        ]  # Index para buscas eficientes
