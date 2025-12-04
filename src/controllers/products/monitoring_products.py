import json

from fastapi import HTTPException, status

from src.model.product import Produto

# Importe seu cliente async do Redis
try:
    from src.core.cache import client
except ImportError:
    print('AVISO: Cliente Redis não encontrado. O cache não funcionará.')
    client = None


class ProductInfo:
    """
    Retrieve stock information for a given user.
    """

    def __init__(self, user_id: int) -> None:
        """Initialize empty values and store user_id."""
        self.products: list = []  # Para o cache de instância
        self.quantity: int = 0
        self.total_stock_price: float = 0.0
        self.user_id: int = user_id
        # Define um tempo de vida para o cache (em segundos)
        self.cache_ttl: int = 600  # 10 minutos

    async def _get_products(self):
        """
        Query the database for all products OR get from instance cache.
        """
        # 1. Cache de Instância: Se já buscamos, retorna da memória
        if self.products:
            return self.products

        # 2. Se não, busca no banco
        try:
            products = await Produto.filter(usuario_id=self.user_id).all()
            self.products = (
                products  # 3. Salva na instância para o próximo uso
            )
            return products
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Database query error: {e}',
            )

    async def count_products(self) -> int:
        """
        Count how many products exist in the user's stock.
        """
        cache_key = f'stock:count:{self.user_id}'

        # 1. Tenta buscar do Cache Redis
        if client:
            try:
                cached_data = await client.get(cache_key)
                if cached_data:
                    print(f'CACHE HIT: {cache_key}')
                    self.quantity = int(cached_data)
                    return self.quantity
            except Exception as e:
                print(f'AVISO: Erro ao buscar do cache (count): {e}')

        print(f'CACHE MISS: {cache_key}')
        # 2. Se falhar (Cache Miss), busca no banco
        products = await self._get_products()
        self.quantity = len(products)

        # 3. Salva no Cache Redis
        if client:
            try:
                await client.setex(cache_key, self.cache_ttl, self.quantity)
            except Exception as e:
                print(f'AVISO: Erro ao salvar no cache (count): {e}')

        return self.quantity

    async def calculate_total_stock_price(self) -> float:
        """
        Calculate the total cost of all products in stock.
        """
        cache_key = f'stock:total_price:{self.user_id}'

        # 1. Tenta buscar do Cache Redis
        if client:
            try:
                cached_data = await client.get(cache_key)
                if cached_data:
                    print(f'CACHE HIT: {cache_key}')
                    self.total_stock_price = float(cached_data)
                    return round(self.total_stock_price, 2)
            except Exception as e:
                print(f'AVISO: Erro ao buscar do cache (price): {e}')

        print(f'CACHE MISS: {cache_key}')
        # 2. Cache Miss
        products = await self._get_products()
        self.total_stock_price = sum(prod.cost_price for prod in products)

        # 3. Salva no Cache Redis
        if client:
            try:
                await client.setex(
                    cache_key, self.cache_ttl, self.total_stock_price
                )
            except Exception as e:
                print(f'AVISO: Erro ao salvar no cache (price): {e}')

        return round(self.total_stock_price, 2)

    async def get_products_by_category(self) -> list[dict]:
        """
        Separate products by category and return their details.
        """
        cache_key = f'stock:by_category:{self.user_id}'

        # 1. Tenta buscar do Cache Redis
        if client:
            try:
                cached_data = await client.get(cache_key)
                if cached_data:
                    print(f'CACHE HIT: {cache_key}')
                    # Se encontramos no cache, não precisamos da lista de ORM
                    # mas atualizamos self.products para o @property funcionar
                    self.products = json.loads(cached_data)
                    return self.products
            except Exception as e:
                print(f'AVISO: Erro ao buscar do cache (category): {e}')

        print(f'CACHE MISS: {cache_key}')
        # 2. Cache Miss
        products = await self._get_products()

        # Formata os dados
        formatted_products = [
            {
                'name': prod.name,
                'category': prod.group,
                'stock': prod.stock,
                'sale_price': prod.sale_price,
                'active': prod.active,
            }
            for prod in products
        ]
        self.products = formatted_products  # Atualiza a variável de instância

        # 3. Salva no Cache Redis
        if client:
            try:
                await client.setex(
                    cache_key,
                    self.cache_ttl,
                    json.dumps(formatted_products, default=str),
                )
            except Exception as e:
                print(f'AVISO: Erro ao salvar no cache (category): {e}')

        return self.products

    @property
    def stock_summary(self) -> dict:
        """
        Property to return a summarized view of the stock data.
        """
        return {
            'user_id': self.user_id,
            'quantity': self.quantity,
            'total_stock_price': self.total_stock_price,
        }

    async def low_product_stock(self) -> int:
        """
        Calcula o número de produtos com estoque baixo.
        """
        cache_key = f'stock:low_count:{self.user_id}'

        # 1. Tenta buscar do Cache Redis
        if client:
            try:
                cached_data = await client.get(cache_key)
                if cached_data:
                    print(f'CACHE HIT: {cache_key}')
                    return int(cached_data)
            except Exception as e:
                print(f'AVISO: Erro ao buscar do cache (low_stock): {e}')

        print(f'CACHE MISS: {cache_key}')
        # 2. Cache Miss
        products = await self._get_products()

        # (Simplifiquei sua lógica de contagem)
        all_products_with_low_stock = sum(
            1 for prod in products if prod.id and prod.stock < prod.stoke_min
        )

        # 3. Salva no Cache Redis
        if client:
            try:
                await client.setex(
                    cache_key, self.cache_ttl, all_products_with_low_stock
                )
            except Exception as e:
                print(f'AVISO: Erro ao salvar no cache (low_stock): {e}')

        return all_products_with_low_stock
