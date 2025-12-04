from tortoise import fields
from tortoise.models import Model

from src.model.user import Usuario


class Ticket(Model):
    """
    Modelo de Tickets vinculado a um usuário (empresa).
    """

    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=150)
    description = fields.TextField(null=True)

    criado_em = fields.DatetimeField(auto_now_add=True)
    atualizado_em = fields.DatetimeField(auto_now=True)

    usuario: fields.ForeignKeyRelation['Usuario'] = fields.ForeignKeyField(
        'models.Usuario', related_name='tickets'
    )

    class Meta:
        table = 'ticket'


#  Tickets padrão do sistema
DEFAULT_TICKETS = [
    {'name': 'Novo', 'description': 'Ticket para produtos novos'},
    {'name': 'Promoção', 'description': 'Ticket para produtos em promoção'},
    {'name': 'Combo', 'description': 'Ticket para combos de produtos'},
    {
        'name': 'Mais Vendido',
        'description': 'Ticket para produtos mais vendidos',
    },
    {'name': 'Oferta Especial', 'description': 'Ticket de ofertas especiais'},
    {'name': 'Sazonal', 'description': 'Ticket para produtos sazonais'},
]


# 🔹 Função para criar tickets padrão para um usuário
async def criar_tickets_padrao(usuario: Usuario):
    for ticket in DEFAULT_TICKETS:
        existe = await Ticket.filter(
            usuario=usuario, name=ticket['name']
        ).first()
        if not existe:
            await Ticket.create(
                usuario=usuario,
                name=ticket['name'],
                description=ticket['description'],
            )
            print('oooooooooooooo')
