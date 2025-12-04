# from src.model.tickets import Ticket

# #  Tickets padrão do sistema
# DEFAULT_TICKETS = [
#     {"name": "Novo", "description": "Ticket para produtos novos"},
#     {"name": "Promoção", "description": "Ticket para produtos em promoção"},
#     {"name": "Combo", "description": "Ticket para combos de produtos"},
#     {"name": "Mais Vendido", "description": "Ticket para produtos mais vendidos"},
#     {"name": "Oferta Especial", "description": "Ticket de ofertas especiais"},
#     {"name": "Sazonal", "description": "Ticket para produtos sazonais"},
# ]


# # 🔹 Função para criar tickets padrão para um usuário
# async def criar_tickets_padrao(usuario):
#     for ticket in DEFAULT_TICKETS:
#         existe = await Ticket.filter(usuario=usuario, name=ticket["name"]).first()
#         if not existe:
#             await Ticket.create(
#                 usuario=usuario,
#                 name=ticket["name"],
#                 description=ticket["description"]
#             )
