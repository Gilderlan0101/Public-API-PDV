# Model carItems
from tortoise import fields
from tortoise.models import Model


class CartItem(Model):
    id = fields.IntField(pk=True, generated=True)
    caixa_id = fields.IntField(null=False)  # Mude user_id para caixa_id
    product_id = fields.IntField(null=False)
    product_name = fields.TextField(null=False)
    quantity = fields.IntField(null=False)
    price = fields.FloatField(null=False)
    total_price = fields.FloatField(null=False, default=0.0)
    discount = fields.FloatField(null=True)
    addition = fields.FloatField(null=True)
    product_code = fields.TextField(null=True)
