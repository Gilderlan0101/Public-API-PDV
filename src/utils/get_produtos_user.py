import json
from typing import Optional

from fastapi import HTTPException, status

from src.core.cache import client
from src.logs.infos import LOGGER
from src.model.product import Produto
from src.model.user import Usuario


async def get_product_by_user(
    user_id: int,
    code: Optional[str] = None,
    name: Optional[str] = None,
    product_id: Optional[int] = None,
):
    """Busca produto pelo usuário, código ou nome."""

    cache_key = f"product:{user_id}:{code or ''}:{name or ''}"
    cache = await client.get(cache_key)

    if cache:
        return json.loads(cache)  # volta dict

    query = Produto.filter(usuario_id=user_id)
    if code:
        query = query.filter(product_code=code)
    if name:
        query = query.filter(name=name)

    if not (code or name):
        query = query.filter(usuario_id=user_id, id=product_id)

    product = await query.first().values()  # <-- pega dict direto

    if product:
        await client.setex(
            cache_key, 90, json.dumps(product, default=str)
        )  # salva no Redis
    return product


async def deep_search(
    user_id: int, product_name: str, target_company: Optional[str] = None
):
    """
    Realiza uma busca aprofundada por um produto...
    """

    # --- 1. Lógica de Cache (Início) ---
    cache_key = None  # Definir fora para usar no 'setex'
    try:
        # Normaliza a chave para evitar duplicatas (ex: "Ham" vs "ham")
        prod_name_key = product_name.lower().strip() if product_name else ''
        company_key = target_company.lower().strip() if target_company else ''

        cache_key = f'product:{user_id}:{prod_name_key}:{company_key}'

        # FIX 1: Adicionar 'await' para realmente buscar no Redis
        cache = await client.get(cache_key)

        if cache:
            LOGGER.info('Retonando dados em cache.')
            return json.loads(cache)  # Agora 'cache' é uma string JSON

        print(f'Cache MISS na função: {cache_key}')

    except Exception as e:
        # Se o cache falhar, não quebre a aplicação. Apenas logue e continue.
        print(f'AVISO: Erro no cache (get): {e}. Buscando no banco...')
    # --- Fim da Lógica de Cache (Início) ---

    try:
        data = []
        user_exists = await Usuario.filter(id=user_id).first()
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Parece que você ainda não possui um cadastro...',
            )

        # Busca sem empresa específica
        if product_name and target_company is None:
            query = await Produto.filter(
                name__icontains=product_name
            ).prefetch_related('usuario')
            if query:
                for product in query:
                    data.append(
                        {
                            'id': product.id,
                            'company': product.usuario.company_name
                            if product.usuario
                            else 'N/A',
                            'name': product.name,
                            'fabricator': product.fabricator
                            if product.fabricator
                            else 'Não informado.',
                            'cost_price': product.cost_price,
                            'price_uni': product.price_uni,
                            'sale_price': product.sale_price,
                            'supplier': product.supplier
                            if product.supplier
                            else 'não informado.',
                            'image_url': f'https://api.nahtec.com.br/produto/{product.id}/imagem',
                        }
                    )

        # Busca com empresa específica
        elif product_name and target_company:
            query = await Produto.filter(
                name__icontains=product_name
            ).prefetch_related('usuario')

            filtered_products = []
            for product in query:
                if (
                    product.usuario
                    and product.usuario.company_name.lower()
                    == target_company.lower()
                ):
                    filtered_products.append(product)

            if filtered_products:
                for product in filtered_products:
                    data.append(
                        {
                            'id': product.id,
                            'company': product.usuario.company_name
                            if product.usuario
                            else 'N/A',
                            'name': product.name,
                            'fabricator': product.fabricator
                            if product.fabricator
                            else 'Não informado.',
                            'cost_price': product.cost_price,
                            'price_uni': product.price_uni,
                            'sale_price': product.sale_price,
                            'supplier': product.supplier
                            if product.supplier
                            else 'Não informado.',
                            'image_url': f'https://api.nahtec.com.br/produto/{product.id}/imagem',
                        }
                    )

        # --- 2. Lógica de Cache (Final) ---
        try:
            if cache_key:
                # FIX 2: Salvar o resultado (mesmo que seja uma lista vazia [])
                # FIX 1: Adicionar 'await' para realmente salvar no Redis
                await client.setex(
                    cache_key, 90, json.dumps(data, default=str)
                )
                print(f'Cache SET na função: {cache_key}')
        except Exception as e:
            print(f'AVISO: Erro no cache (setex): {e}')
        # --- Fim da Lógica de Cache (Final) ---

        return data  # Retorna os dados (sejam eles [] ou cheios)

    except HTTPException:
        raise
    except Exception as e:
        print(f'Erro na busca aprofundada: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno durante a busca: {str(e)}',
        )
