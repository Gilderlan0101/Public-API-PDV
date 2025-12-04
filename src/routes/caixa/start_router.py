# src/routes/start_router.py
import logging

from fastapi import APIRouter

from src.routes.caixa.box_closing import router as close
from src.routes.caixa.checkout_report import router as report
from src.routes.caixa.informations import router as info
from src.routes.caixa.login import LoginCheckout
from src.routes.caixa.status import router as status
from src.routes.caixa.summary import router as summary

logger = logging.getLogger(__name__)

# Agrupamento geral do checkout
checkout = APIRouter(
    tags=['Caixa'],
    responses={404: {'description': 'Não encontrado'}},
    prefix='/checkout',
)

# Instancia a classe e pega o router interno
login_checkout = LoginCheckout()

# Inclui as rotas internas
checkout.include_router(login_checkout.router)
checkout.include_router(report)
checkout.include_router(info)
checkout.include_router(summary)
checkout.include_router(status)
checkout.include_router(close)
