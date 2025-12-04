import json  # 1. Precisamos do JSON para converter os dados
from typing import Optional

from fastapi import HTTPException

from src.utils.get_produtos_user import deep_search

try:
    # Tenta importar da estrutura de pastas (ex: src/utils/redis_client.py)
    from src.core.cache import client
except ImportError:
    # Se falhar, tenta importar do mesmo nível (ex: redis_client.py)
    print(
        "Aviso: Importando 'client' do diretório raiz. Ajuste se necessário."
    )


class CustomerMarketplace:
    def __init__(
        self,
        user_id: int,
        product_name: str,
        target_company: Optional[str] = None,
    ):
        self.user_id = user_id
        self.product_name = product_name
        self.target_company = target_company
        # Definir um tempo de expiração para o cache (em segundos)
        # 3600 segundos = 1 hora
        self.cache_ttl = 3600

    async def result(self):
        # 3. Criar uma chave de cache única
        # É importante incluir todos os parâmetros para a busca ser única
        company_part = self.target_company if self.target_company else 'all'
        cache_key = f'cache:user_products:{self.user_id}:{self.product_name.lower().strip()}:{company_part.lower().strip()}'

        # 4. Tentar buscar do Cache PRIMEIRO
        if client:  # Só tenta o cache se o 'client' não for None (conexão OK)
            try:
                cached_result = await client.get(cache_key)
                if cached_result:
                    print(f'CACHE HIT para a chave: {cache_key}')
                    # O 'client' foi configurado com decode_responses=True,
                    # então o JSON já vem como string.
                    return json.loads(cached_result)
            except Exception as e:
                # Se o Redis falhar, apenas loga e segue para a busca no DB
                print(f'Erro ao buscar do cache: {e}')

        print(f'CACHE MISS para a chave: {cache_key}')

        # 5. CACHE MISS: Buscar no banco (sua lógica original)
        products = None
        if self.product_name and self.target_company:
            products = await deep_search(
                user_id=self.user_id,
                product_name=self.product_name,
                target_company=self.target_company,
            )
        elif self.product_name:
            products = await deep_search(
                user_id=self.user_id, product_name=self.product_name
            )

        # 6. Salvar o resultado no Cache ANTES de retornar
        #    (Apenas se a busca no banco retornar algo)
        if client and products is not None:
            try:
                # Convertemos a lista de produtos para uma string JSON
                await client.set(
                    cache_key, json.dumps(products), ex=self.cache_ttl
                )
                print(f'CACHE SET para a chave: {cache_key}')
            except Exception as e:
                # Se falhar ao salvar, não quebra a aplicação
                print(f'Erro ao salvar no cache: {e}')

        return products
