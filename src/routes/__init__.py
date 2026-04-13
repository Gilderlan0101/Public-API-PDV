# src/__init__/routes/__init__.py
from typing import Any, Dict, List

from fastapi import APIRouter


class RouterManager:
    """Gerenciador centralizado de rotas com configuração profissional"""

    def __init__(self):
        self.routers: Dict[str, APIRouter] = {}
        self._configure_routers()

    def _configure_routers(self):
        """Configura todas as rotas do sistema"""

        # ===== AUTENTICAÇÃO =====
        from .login import Login
        from .registre import registerRT

        login_handler = Login()

        self.routers['auth'] = APIRouter(
            prefix='/api/v1/auth',
            tags=['🔐 Autenticação'],
            responses={
                400: {'description': 'Requisição inválida'},
                401: {'description': 'Não autorizado'},
                404: {'description': 'Recurso não encontrado'},
                500: {'description': 'Erro interno do servidor'},
            },
            dependencies=[],  # Pode adicionar dependências globais aqui
        )
        self.routers['auth'].include_router(login_handler.loginRT)
        self.routers['auth'].include_router(registerRT)

        # ===== FUNCIONÁRIOS =====
        from .account.account import employees_router as account
        from .account.employee_edit import employees_router as edit_employees
        from .account.employee_list import employees_router

        self.routers['funcionarios'] = APIRouter(
            prefix='/api/v1/funcionarios',
            tags=['👥 Funcionários'],
            responses={404: {'description': 'Funcionário não encontrado'}},
        )
        self.routers['funcionarios'].include_router(employees_router)
        self.routers['funcionarios'].include_router(edit_employees)
        self.routers['funcionarios'].include_router(account)

        # ===== CLIENTES =====
        from .cliente_cnpj import ConsultaRoute
        from .customer.customer_registration import customers
        from .customer.registre_customer_partial import (
            customers as registre_user_partial,
        )

        consulta_handler = ConsultaRoute()

        self.routers['clientes'] = APIRouter(
            prefix='/api/v1/clientes',
            tags=['👥 Clientes'],
            responses={404: {'description': 'Cliente não encontrado'}},
        )
        self.routers['clientes'].include_router(consulta_handler.router)
        self.routers['clientes'].include_router(customers)
        self.routers['clientes'].include_router(registre_user_partial)

        # ===== PRODUTOS =====
        from .products.buscar_prod import buscar_produtos
        from .products.cancel_sale import router as cancel_sales
        from .products.create import router as create_products
        from .products.deep_infos import product_deep_infos
        from .products.delete import router as delete_products
        from .products.list import list_products as list_router
        from .products.product_information import list_products as product_info
        from .products.sales import router as sales
        from .products.ticket import router as ticket_prods
        from .products.update import router as updates_products
        from .products.upload_img import router as upload_img

        self.routers['produtos'] = APIRouter(
            prefix='/api/v1/produtos',
            tags=['📦 Produtos'],
            responses={404: {'description': 'Produto não encontrado'}},
        )
        self.routers['produtos'].include_router(upload_img)
        self.routers['produtos'].include_router(buscar_produtos)
        self.routers['produtos'].include_router(list_router)
        self.routers['produtos'].include_router(product_info)
        self.routers['produtos'].include_router(create_products)
        self.routers['produtos'].include_router(updates_products)
        self.routers['produtos'].include_router(delete_products)
        self.routers['produtos'].include_router(product_deep_infos)
        self.routers['produtos'].include_router(ticket_prods)

        # ===== CARRINHO & VENDAS =====
        from .car import cart_router
        from .car.pdv import router as result_sales

        self.routers['carrinho'] = APIRouter(
            prefix='/api/v1/carrinho',
            tags=['🛒 Carrinho & Vendas'],
            responses={404: {'description': 'Carrinho não encontrado'}},
        )
        self.routers['carrinho'].include_router(cart_router)
        self.routers['carrinho'].include_router(sales)
        self.routers['carrinho'].include_router(cancel_sales)
        self.routers['carrinho'].include_router(result_sales)

        # ===== FORNECEDORES =====
        from .fornecedor.registre_fornecedor import router as fornecedores_rt

        self.routers['fornecedor'] = APIRouter(
            prefix='/api/v1/fornecedores',
            tags=['🏢 Fornecedores'],
            responses={404: {'description': 'Fornecedor não encontrado'}},
        )
        self.routers['fornecedor'].include_router(fornecedores_rt)

        # ===== DASHBOARD & RELATÓRIOS =====
        from .updates import allDatas
        from .user.clientes import router as system_user

        self.routers['dashboard'] = APIRouter(
            prefix='/api/v1/dashboard',
            tags=['📊 Dashboard & Analytics'],
            responses={404: {'description': 'Dados não encontrados'}},
        )
        self.routers['dashboard'].include_router(allDatas)
        self.routers['dashboard'].include_router(system_user)

        # ===== PAGAMENTOS =====
        from .payments.partial import partial as payment_partial
        from .payments.pix import router as payment_pix

        self.routers['pagamentos'] = APIRouter(
            prefix='/api/v1/pagamentos',
            tags=['💳 Pagamentos'],
            responses={
                400: {'description': 'Pagamento inválido'},
                402: {'description': 'Pagamento necessário'},
                422: {'description': 'Dados de pagamento inválidos'},
            },
        )
        self.routers['pagamentos'].include_router(payment_partial)
        self.routers['pagamentos'].include_router(payment_pix)

        # ===== DELIVERY =====
        from .delivery.create_delivery import delivery_router

        self.routers['delivery'] = APIRouter(
            prefix='/api/v1/delivery',
            tags=['🚚 Delivery'],
            responses={404: {'description': 'Entrega não encontrada'}},
        )
        self.routers['delivery'].include_router(delivery_router)

        # ===== MARKETPLACE =====
        from .marketplace.marketplace_between_customers import marketplace

        self.routers['marketplace'] = APIRouter(
            prefix='/api/v1/marketplace',
            tags=['🛍️ Marketplace'],
            responses={404: {'description': 'Marketplace não encontrado'}},
        )
        self.routers['marketplace'].include_router(marketplace)

        # ===== INVENTÁRIO =====
        from .products.inventario.label_generator import (
            inventory_router as label,
        )
        from .products.inventario.stock_entry_controller import (
            inventory_router as stoke,
        )
        from .products.inventario.stock_exit_controller import (
            inventory_router as exit_router,
        )

        self.routers['inventario'] = APIRouter(
            prefix='/api/v1/inventario',
            tags=['📋 Inventário'],
            responses={
                404: {'description': 'Item não encontrado no inventário'}
            },
        )
        self.routers['inventario'].include_router(stoke)
        self.routers['inventario'].include_router(label)
        self.routers['inventario'].include_router(exit_router)

        # ===== CAIXA =====
        from .caixa.start_router import checkout

        self.routers['caixa'] = APIRouter(
            prefix='/api/v1/caixa',
            tags=['💰 Caixa'],
            responses={404: {'description': 'Caixa não encontrado'}},
        )
        self.routers['caixa'].include_router(checkout)

    def get_all_routers(self) -> List[APIRouter]:
        """Retorna todos os routers configurados"""
        return list(self.routers.values())

    def get_router(self, name: str) -> APIRouter:
        """Retorna um router específico pelo nome"""
        return self.routers.get(name)

    def get_routers_dict(self) -> Dict[str, APIRouter]:
        """Retorna dicionário com todos os routers"""
        return self.routers.copy()


# Instância global do gerenciador de rotas
router_manager = RouterManager()

# ===== EXPORTAÇÕES PARA BACKWARD COMPATIBILITY =====
# Mantém a interface antiga para não quebrar o código existente

# Routers principais (compatibilidade)
auth = router_manager.get_router('auth')
Funcionários = router_manager.get_router('funcionarios')
clientes = router_manager.get_router('clientes')
produtos = router_manager.get_router('produtos')
carrinho = router_manager.get_router('carrinho')
fornecedor = router_manager.get_router('fornecedor')
tickets = router_manager.get_router('produtos')  # Tickets está em produtos
dashboard = router_manager.get_router('dashboard')
paymente = router_manager.get_router('pagamentos')
delivery = router_manager.get_router('delivery')
marketplace = router_manager.get_router('marketplace')
my_inventario = router_manager.get_router('inventario')

# Export para import fácil
__all__ = [
    # Gerenciador
    'router_manager',
    # Routers principais
    'auth',
    'Funcionários',
    'clientes',
    'produtos',
    'carrinho',
    'fornecedor',
    'tickets',
    'dashboard',
    'paymente',
    'delivery',
    'marketplace',
    'my_inventario',
    # Routers individuais para acesso direto
    'auth',
    'Funcionários',
    'clientes',
    'produtos',
    'carrinho',
    'fornecedor',
    'dashboard',
    'paymente',
    'delivery',
    'marketplace',
    'my_inventario',
]

# ===== CONFIGURAÇÃO DE METADADOS =====
API_METADATA = {
    'title': 'Nahtec PDV API',
    'version': '1.0.0',
    'description': """
    🚀 **Nahtec PDV - Sistema Completo de Ponto de Venda**

    ## Recursos Principais

    ### 🛒 Vendas & Carrinho
    - Gestão completa de vendas
    - Carrinho dinâmico
    - Cancelamento de vendas

    ### 📦 Produtos & Estoque
    - Cadastro e gestão de produtos
    - Controle de inventário
    - Upload de imagens

    ### 👥 Clientes & Funcionários
    - CRM integrado
    - Gestão de equipe
    - Controle de acesso

    ### 💳 Pagamentos
    - Múltiplos métodos de pagamento
    - Pix integrado
    - Pagamentos parcelados

    ### 🚚 Delivery
    - Gestão de entregas
    - Rastreamento
    - Controle de status

    ### 📊 Dashboard & Analytics
    - Relatórios em tempo real
    - Métricas de performance
    - Analytics de vendas
    """,
    'contact': {
        'name': 'Suporte Nahtec',
        'email': 'contatodevorbit@gmail.com',
        'url': 'https://github.com/Gilderlan0101/qodo-pdv',
    },
    'license_info': {
        'name': 'MIT',
        'url': 'https://opensource.org/licenses/MIT',
    },
    'terms_of_service': 'https://github.com/Gilderlan0101/qodo-pdv/blob/main/TERMS.md',
    'docs_url': '/docs',
    'redoc_url': '/redoc',
    'openapi_url': '/api/v1/openapi.json',
    'openapi_tags': [
        {
            'name': '🔐 Autenticação',
            'description': 'Operações de autenticação e gestão de usuários',
        },
        {
            'name': '👥 Funcionários',
            'description': 'Gestão de funcionários e equipe',
        },
        {'name': '👥 Clientes', 'description': 'Gestão de clientes e CRM'},
        {
            'name': '📦 Produtos',
            'description': 'Operações relacionadas a produtos e estoque',
        },
        {
            'name': '🛒 Carrinho & Vendas',
            'description': 'Gestão de carrinho e processo de vendas',
        },
        {
            'name': '🏢 Fornecedores',
            'description': 'Gestão de fornecedores e supply chain',
        },
        {
            'name': '📊 Dashboard & Analytics',
            'description': 'Relatórios e analytics em tempo real',
        },
        {
            'name': '💳 Pagamentos',
            'description': 'Processamento de pagamentos e financeiro',
        },
        {
            'name': '🚚 Delivery',
            'description': 'Gestão de entregas e logística',
        },
        {
            'name': '🛍️ Marketplace',
            'description': 'Operações de marketplace e e-commerce',
        },
        {
            'name': '📋 Inventário',
            'description': 'Controle de inventário e estoque',
        },
        {
            'name': '💰 Caixa',
            'description': 'Gestão de caixa e fluxo financeiro',
        },
    ],
}


def get_api_metadata() -> Dict[str, Any]:
    """Retorna metadados configurados para o FastAPI"""
    return API_METADATA.copy()


def setup_routes(app):
    """
    Configura todas as rotas na aplicação FastAPI

    Usage:
        from src..routes import setup_routes
        setup_routes(app)
    """
    for router in router_manager.get_all_routers():
        app.include_router(router)

    return app
