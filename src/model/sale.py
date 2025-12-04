from enum import StrEnum

from tortoise import fields, models


class PaymentMethods(StrEnum):
    PIX = 'PIX'
    CARTAO = 'CARTAO'
    DINHEIRO = 'DINHEIRO'
    NOTA = 'NOTA'
    FIADO = 'FIADO'


class Sales(models.Model):
    """
    Modelo de vendas do PDV.
    Cada venda está vinculada a um usuário (empresa),
    pode ou não ter um funcionário associado,
    e deve sempre estar ligada a um produto.
    """

    id = fields.IntField(pk=True)
    product_name = fields.CharField(max_length=150)
    quantity = fields.IntField(default=1)
    total_price = fields.FloatField()
    lucro_total = fields.FloatField(default=0.0)
    cost_price = fields.FloatField()
    sale_code = fields.CharField(max_length=6, null=True, index=True)
    payment_method = fields.CharEnumField(PaymentMethods, max_length=9)
    criado_em = fields.DatetimeField(auto_now_add=True)

    # 🔹 Relacionamento com o usuário (empresa dono da venda)
    usuario = fields.ForeignKeyField(
        'models.Usuario', related_name='vendas', on_delete=fields.CASCADE
    )

    # 🔹 Relacionamento com o funcionário operador (opcional)
    funcionario = fields.ForeignKeyField(
        'models.Employees',
        related_name='vendas',
        null=True,
        on_delete=fields.SET_NULL,
    )

    # 🔹 Relacionamento com o produto (obrigatório)
    produto = fields.ForeignKeyField(
        'models.Produto',
        related_name='vendas',
        null=False,
        on_delete=fields.RESTRICT,  # impede apagar produto se houver vendas
    )

    caixa = fields.ForeignKeyField(
        'models.Caixa',
        related_name='vendas',
        null=True,
        on_delete=fields.SET_NULL,
    )  # Pode ser null se não tiver caixa

    class Meta:
        table = 'sales'
        ordering = ['-criado_em']
