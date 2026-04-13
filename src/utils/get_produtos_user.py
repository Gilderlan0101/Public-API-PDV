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
    Prioriza a busca por código ou nome, utilizando cache Redis para performance.
    """

    # Geracao da chave de cache baseada nos parametros de busca
    cache_key = f"product:{user_id}:{code or ''}:{name or ''}"

    # Tentativa de recuperacao de dados do cache Redis
    cache = await client.get(cache_key)

    if cache:
        # Retorna o dicionario desserializado se encontrado no cache
        return json.loads(cache)

    # Inicializacao da query filtrando pelo ID do usuario logado
    query = Produto.filter(usuario_id=user_id)

    if code:
        query = query.filter(product_code=code)
    if name:
        query = query.filter(name=name)

    # Caso nenhum parametro de identificacao seja fornecido, a busca e abortada
    if not (code or name):
        # query = query.filter(usuario_id=user_id, id=product_id)
        return None

    # Execucao da query no banco de dados
    # Armazenamos o resultado do first() para verificar existencia antes de chamar .values()
    result = await query.first()

    if not result:
        return None

    # Converte o objeto do modelo para dicionario
    product = await result.values()

    # Persistencia no cache com tempo de expiracao de 90 segundos
    if product:
        await client.setex(cache_key, 90, json.dumps(product, default=str))

    return product


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
