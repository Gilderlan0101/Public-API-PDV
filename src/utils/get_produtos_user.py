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
    """
    Busca um produto específico vinculado a um usuário.
    Usa .values() para garantir que o retorno seja um dicionário puro,
    facilitando o cache e a velocidade.
    """

    # 1. Normalização dos parâmetros para a chave de cache
    search_code = str(code).strip() if code else ''
    search_name = str(name).strip().lower() if name else ''

    cache_key = (
        f"product:{user_id}:{search_code}:{search_name}:{product_id or ''}"
    )

    # 2. Tentativa de recuperação rápida no Cache
    try:
        cache = await client.get(cache_key)
        if cache:
            return json.loads(cache)
    except Exception as e:
        LOGGER.error(f'Erro ao ler cache: {e}')

    # 3. Construção da Query
    query = Produto.filter(usuario_id=user_id)

    if code:
        query = query.filter(product_code=search_code)
    elif name:
        query = query.filter(name__icontains=search_name)
    elif product_id:
        query = query.filter(id=product_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Forneça o código, nome ou ID do produto.',
        )

    # 4. Execução: .values() extrai os dados como dict direto do banco (mais rápido)
    product_data = await query.values()

    if not product_data:
        label = search_code or search_name or product_id
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Produto {label} não encontrado.',
        )

    # 5. Salva no Cache por 1 hora (3600s)
    try:
        # Usamos default=str para lidar com campos de data/datetime no dicionário
        await client.setex(
            cache_key, 3600, json.dumps(product_data, default=str)
        )
    except Exception as e:
        LOGGER.error(f'Erro ao salvar no cache: {e}')

    return product_data


async def deep_search(
    user_id: int, product_name: str, target_company: Optional[str] = None
):
    """
    Realiza busca aprofundada por nome de produto em toda a base.
    Permite filtrar por uma empresa especifica ou buscar de forma global.
    """

    # Configuracao inicial da chave de cache para a busca profunda
    cache_key = None
    try:
        # Normalizacao de strings para garantir integridade da chave de cache
        prod_name_key = product_name.lower().strip() if product_name else ''
        company_key = target_company.lower().strip() if target_company else ''

        cache_key = f'product:{user_id}:{prod_name_key}:{company_key}'

        # Busca assincrona no Redis
        cache = await client.get(cache_key)

        if cache:
            LOGGER.info('Dados recuperados via cache Redis.')
            return json.loads(cache)

    except Exception as e:
        # Falhas no cache nao impedem a execucao da busca no banco de dados
        LOGGER.error(f'Falha na leitura do cache: {e}')

    try:
        data = []

        # Verificacao de existencia e permissao do usuario requisitante
        user_exists = await Usuario.filter(id=user_id).first()
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Usuario nao identificado ou sem permissao de acesso.',
            )

        # Filtro base utilizando busca parcial (icontains) e carregamento de relacionamento
        if product_name:
            query_base = Produto.filter(
                name__icontains=product_name
            ).prefetch_related('usuario')

            # Caso nao haja empresa alvo, retorna todos os produtos que coincidem com o nome
            if target_company is None:
                results = await query_base
                for product in results:
                    data.append(
                        {
                            'id': product.id,
                            'company': product.usuario.company_name
                            if product.usuario
                            else 'N/A',
                            'name': product.name,
                            'fabricator': product.fabricator or 'N/A',
                            'cost_price': product.cost_price,
                            'price_uni': product.price_uni,
                            'sale_price': product.sale_price,
                            'supplier': product.supplier or 'N/A',
                            'image_url': f'https://api.nahtec.com.br/produto/{product.id}/imagem',
                        }
                    )

            # Caso haja empresa alvo, filtra os resultados em memoria
            else:
                results = await query_base
                target_lower = target_company.lower()

                for product in results:
                    if (
                        product.usuario
                        and product.usuario.company_name.lower()
                        == target_lower
                    ):
                        data.append(
                            {
                                'id': product.id,
                                'company': product.usuario.company_name,
                                'name': product.name,
                                'fabricator': product.fabricator or 'N/A',
                                'cost_price': product.cost_price,
                                'price_uni': product.price_uni,
                                'sale_price': product.sale_price,
                                'supplier': product.supplier or 'N/A',
                                'image_url': f'https://api.nahtec.com.br/produto/{product.id}/imagem',
                            }
                        )

        # Atualizacao do cache com o resultado da busca (lista vazia ou preenchida)
        try:
            if cache_key:
                await client.setex(
                    cache_key, 90, json.dumps(data, default=str)
                )
        except Exception as e:
            LOGGER.error(f'Falha ao gravar dados no cache: {e}')

        return data

    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f'Erro critico na busca aprofundada: {str(e)}')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f'Erro interno durante o processamento da busca.',
        )
