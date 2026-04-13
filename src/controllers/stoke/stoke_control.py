import json
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from tortoise.exceptions import DoesNotExist

from src.core.cache import client
from src.model.product import Produto
from src.model.user import Usuario
from src.logs.infos import LOGGER

# Configuracao de fuso horario e tempo de cache
TZ = ZoneInfo('America/Sao_Paulo')
CACHE_TTL = 180  # Segundos


async def get_user(user_id: int) -> Optional[Usuario]:
    """
    Recupera a instancia do modelo Usuario atraves do ID.
    Retorna None caso o registro nao exista no banco de dados.
    """
    try:
        return await Usuario.get(id=user_id)
    except DoesNotExist:
        LOGGER.warning(
            f'Usuario {user_id} nao encontrado para geracao de relatorio.'
        )
        return None


async def get_user_products(user: Usuario) -> List[Dict]:
    """
    Recupera todos os produtos vinculados a um usuario.
    Utiliza cache Redis baseado no ID do usuario para otimizacao de performance.
    """
    if not user:
        return []

    cache_key = f'user_products:{user.id}'
    try:
        cache = await client.get(cache_key)
        if cache:
            return json.loads(cache)
    except Exception as e:
        LOGGER.error(f'Erro ao acessar cache em get_user_products: {e}')

    produtos = await Produto.filter(usuario_id=user.id).all()

    # Mapeamento para dicionario para facilitar processamento e serializacao
    data = [
        {
            'id': p.id,
            'name': p.name,
            'stock_atual': p.stock,
            'stock_min': p.stoke_min,
            'stock_max': p.stoke_max,
            'date_expired': p.date_expired,
            'price_uni': p.price_uni,
        }
        for p in produtos
    ]

    if data:
        try:
            await client.setex(
                cache_key, CACHE_TTL, json.dumps(data, default=str)
            )
        except Exception as e:
            LOGGER.error(
                f'Falha ao persistir cache de produtos do usuario {user.id}: {e}'
            )

    return data


async def check_replacement(user_id: int, produtos: List[Dict]) -> List[Dict]:
    """
    Analisa os níveis de estoque comparando o saldo atual com o mínimo definido.
    Retorna uma lista de status por produto com alertas de reposição.
    """
    cache_key = f'stock_replacement_status:{user_id}'
    try:
        cache = await client.get(cache_key)
        if cache:
            return json.loads(cache)
    except Exception as e:
        LOGGER.error(f'Erro no cache de reposicao: {e}')

    status_estoque = []
    for product in produtos:
        stock_atual = product.get('stock_atual', 0)
        stock_min = product.get('stock_min', 0)
        name = product.get('name', 'N/A')

        needs_replacement = stock_atual <= stock_min

        item_status = {
            'product_name': name.capitalize(),
            'current_stock': stock_atual,
            'status': 'Reposicao necessaria'
            if needs_replacement
            else 'Estoque OK',
        }

        if needs_replacement:
            item_status[
                'alert'
            ] = f"Produto '{name}' abaixo do nivel minimo permitido."

        status_estoque.append(item_status)

    if status_estoque:
        await client.setex(
            cache_key, CACHE_TTL, json.dumps(status_estoque, default=str)
        )

    return status_estoque


async def expired_products(user_id: int, produtos: List[Dict]) -> Dict:
    """
    Identifica produtos com data de validade vencida ou proxima ao vencimento (10 dias).
    Calcula o valor financeiro em perda e o valor em risco.
    """
    cache_key = f'expired_report:{user_id}'
    try:
        cache = await client.get(cache_key)
        if cache:
            return json.loads(cache)
    except Exception as e:
        LOGGER.error(f'Erro no cache de validade: {e}')

    data_atual = datetime.now(TZ).date()
    produtos_vencendo = []
    produtos_vencidos = []
    valor_total_vencido = 0.0
    valor_total_potencial = 0.0

    for product in produtos:
        raw_date = product.get('date_expired')
        if not raw_date:
            continue

        # Normalizacao da data para comparacao
        data_validade = (
            raw_date.date() if isinstance(raw_date, datetime) else raw_date
        )
        dias_restantes = (data_validade - data_atual).days
        valor_lote = float(product.get('stock_atual', 0)) * float(
            product.get('price_uni', 0)
        )

        item_data = {
            'name': product['name'],
            'expired_date': data_validade.strftime('%Y-%m-%d'),
            'stock': product['stock_atual'],
            'price': product['price_uni'],
            'valor_lote': valor_lote,
            'dias_restantes': dias_restantes,
        }

        if dias_restantes < 0:
            item_data[
                'alert'
            ] = f"Produto '{product['name']}' vencido ha {abs(dias_restantes)} dias."
            produtos_vencidos.append(item_data)
            valor_total_vencido += valor_lote
        elif dias_restantes <= 10:
            item_data[
                'alert'
            ] = f"Produto '{product['name']}' vencera em {dias_restantes} dias."
            produtos_vencendo.append(item_data)
            valor_total_potencial += valor_lote

    report = {
        'produtos_vencendo': produtos_vencendo,
        'produtos_vencidos': produtos_vencidos,
        'valor_total_vencido': valor_total_vencido,
        'valor_total_potencial': valor_total_potencial,
    }

    try:
        await client.setex(
            cache_key, CACHE_TTL, json.dumps(report, default=str)
        )
    except Exception as e:
        LOGGER.error(f'Erro ao salvar relatorio de validade no cache: {e}')

    return report


async def gerar_relatorio_completo(user_id: int) -> Dict:
    """
    Consolida as analises de estoque e validade em um unico objeto de resposta.
    """
    user = await get_user(user_id)
    if not user:
        return {'error': 'Usuario nao encontrado para consolidacao de dados.'}

    produtos_usuario = await get_user_products(user)

    # Execucao das analises baseadas na lista de produtos ja recuperada
    return {
        'estoque': await check_replacement(user_id, produtos_usuario),
        'validade': await expired_products(user_id, produtos_usuario),
    }
