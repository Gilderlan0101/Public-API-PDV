from fastapi import APIRouter

# Importacao das rotas de registro de clientes
from .customer_registration import customers as registration_router

"""
Este modulo agrupa todas as rotas relacionadas a gestao de clientes.
Configuracoes de prefixo e tags sao gerenciadas pelo RouterManager principal.
"""

customers = APIRouter(
    responses={404: {'description': 'Customer resource not found'}},
)

# Inclusao dos sub-routers de clientes
customers.include_router(registration_router)
