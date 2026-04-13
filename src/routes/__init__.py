from typing import Any, Dict, List

from fastapi import APIRouter, FastAPI

from src.logs.infos import LOGGER

# Metadata configuration for documentation
API_METADATA = {
    'title': 'DevOrbit tech',
    'version': '1.0.0',
    'description': """
    DevOrbir tech - Complete Point of Sale System

    Main Features:
    - Sales and Cart Management
    - Inventory and Product Control
    - CRM and Employee Management
    - Integrated Payments (Pix, Partial, Card)
    - Delivery Logistics
    - Real-time Dashboard and Analytics
    """,
    'contact': {
        'name': 'Orbit PDV',
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
}


class RouterManager:
    """Centralized route manager with professional configuration"""

    def __init__(self):
        self.routers: Dict[str, APIRouter] = {}
        self._configure_routers()

    def _configure_routers(self):
        """Configures all system routes with standardized settings"""

        # --- Authentication ---
        from .login import Login
        from .registre import registerRT

        auth_router = APIRouter(
            prefix='/api/v1/auth',
            tags=['Authentication'],
            responses={
                401: {'description': 'Unauthorized'},
                403: {'description': 'Forbidden'},
                500: {'description': 'Internal Server Error'},
            },
        )
        auth_router.include_router(Login().loginRT)
        auth_router.include_router(registerRT)
        self.routers['auth'] = auth_router

        # --- Employees ---
        from .account.account import employees_router as account
        from .account.employee_edit import employees_router as edit_employees
        from .account.employee_list import employees_router as list_employees

        employees_router = APIRouter(
            prefix='/api/v1/employees', tags=['Employees']
        )
        employees_router.include_router(list_employees)
        employees_router.include_router(edit_employees)
        employees_router.include_router(account)
        self.routers['employees'] = employees_router

        # --- Customers ---
        from .cliente_cnpj import ConsultaRoute
        from .customer.customer_registration import customers
        from .customer.registre_customer_partial import \
            customers as partial_registration

        customers_router = APIRouter(
            prefix='/api/v1/customers', tags=['Customers']
        )
        customers_router.include_router(ConsultaRoute().router)
        customers_router.include_router(customers)
        customers_router.include_router(partial_registration)
        self.routers['customers'] = customers_router

        # --- Products ---
        from .products.buscar_prod import buscar_produtos
        from .products.create import router as create_products
        from .products.deep_infos import product_deep_infos
        from .products.delete import router as delete_products
        from .products.list import list_products as list_router
        from .products.product_information import list_products as product_info
        from .products.ticket import router as ticket_prods
        from .products.update import router as updates_products
        from .products.upload_img import router as upload_img

        products_router = APIRouter(
            prefix='/api/v1/products', tags=['Products']
        )
        products_router.include_router(upload_img)
        products_router.include_router(buscar_produtos)
        products_router.include_router(list_router)
        products_router.include_router(product_info)
        products_router.include_router(create_products)
        products_router.include_router(updates_products)
        products_router.include_router(delete_products)
        products_router.include_router(product_deep_infos)
        products_router.include_router(ticket_prods)
        self.routers['products'] = products_router

        # --- Cart and Sales ---
        from .car import cart_router
        from .car.pdv import router as sales_results
        from .products.cancel_sale import router as cancel_sales
        from .products.sales import router as process_sales

        cart_router_group = APIRouter(
            prefix='/api/v1/cart', tags=['Cart and Sales']
        )
        cart_router_group.include_router(cart_router)
        cart_router_group.include_router(process_sales)
        cart_router_group.include_router(cancel_sales)
        cart_router_group.include_router(sales_results)
        self.routers['cart'] = cart_router_group

        # --- Suppliers ---
        from .fornecedor.registre_fornecedor import router as suppliers_rt

        suppliers_router = APIRouter(
            prefix='/api/v1/suppliers', tags=['Suppliers']
        )
        suppliers_router.include_router(suppliers_rt)
        self.routers['suppliers'] = suppliers_router

        # --- Dashboard and Analytics ---
        from .updates import allDatas
        from .user.clientes import router as system_user

        dashboard_router = APIRouter(
            prefix='/api/v1/dashboard', tags=['Dashboard']
        )
        dashboard_router.include_router(allDatas)
        dashboard_router.include_router(system_user)
        self.routers['dashboard'] = dashboard_router

        # --- Payments ---
        from .payments.partial import partial as payment_partial
        from .payments.pix import router as payment_pix

        payments_router = APIRouter(
            prefix='/api/v1/payments',
            tags=['Payments'],
            responses={400: {'description': 'Invalid Payment Data'}},
        )
        payments_router.include_router(payment_partial)
        payments_router.include_router(payment_pix)
        self.routers['payments'] = payments_router

        # --- Delivery ---
        from .delivery.create_delivery import delivery_router

        delivery_router_group = APIRouter(
            prefix='/api/v1/delivery', tags=['Delivery']
        )
        delivery_router_group.include_router(delivery_router)
        self.routers['delivery'] = delivery_router_group

        # --- Marketplace ---
        from .marketplace.marketplace_between_customers import marketplace

        mkt_router = APIRouter(
            prefix='/api/v1/marketplace', tags=['Marketplace']
        )
        mkt_router.include_router(marketplace)
        self.routers['marketplace'] = mkt_router

        # --- Inventory ---
        from .products.inventario.label_generator import \
            inventory_router as labels
        from .products.inventario.stock_entry_controller import \
            inventory_router as entry
        from .products.inventario.stock_exit_controller import \
            inventory_router as exit_ctrl

        inventory_router = APIRouter(
            prefix='/api/v1/inventory', tags=['Inventory']
        )
        inventory_router.include_router(entry)
        inventory_router.include_router(labels)
        inventory_router.include_router(exit_ctrl)
        self.routers['inventory'] = inventory_router

        # --- Cashier ---
        from .caixa.start_router import checkout

        cashier_router = APIRouter(prefix='/api/v1/cashier', tags=['Cashier'])
        cashier_router.include_router(checkout)
        self.routers['cashier'] = cashier_router

    def get_all_routers(self) -> List[APIRouter]:
        return list(self.routers.values())


# Global instance
router_manager = RouterManager()

# --- Backward Compatibility Exports ---
auth = router_manager.routers.get('auth')
employees = router_manager.routers.get('employees')
customers = router_manager.routers.get('customers')
products = router_manager.routers.get('products')
cart = router_manager.routers.get('cart')
suppliers = router_manager.routers.get('suppliers')
dashboard = router_manager.routers.get('dashboard')
payments = router_manager.routers.get('payments')
delivery = router_manager.routers.get('delivery')
marketplace = router_manager.routers.get('marketplace')
inventory = router_manager.routers.get('inventory')
cashier = router_manager.routers.get('cashier')


def setup_routes(app: FastAPI):
    """Integrates all routers into the FastAPI application"""
    for router in router_manager.get_all_routers():
        app.include_router(router)
    return app


def get_api_metadata() -> Dict[str, Any]:
    return API_METADATA.copy()


__all__ = [
    'router_manager',
    'setup_routes',
    'get_api_metadata',
    'auth',
    'employees',
    'customers',
    'products',
    'cart',
    'suppliers',
    'dashboard',
    'payments',
    'delivery',
    'marketplace',
    'inventory',
    'cashier',
]
