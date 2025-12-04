# Este é o conteúdo completo para /src/core/cache.py

import os

import redis.asyncio as redis  # <--- Importa a versão ASYNC
from dotenv import load_dotenv

load_dotenv()  # Carrega o .env

# Lê a URL do ambiente
REDIS_URL = os.getenv(
    'CACHE_REDIS',
)

# Define o tipo do cliente para ajudar o editor de código
client: redis.Redis = None

try:
    # Cria a instância do cliente (pool de conexão)
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    if client:
        print('Redis [ OK ]')

except Exception as e:
    print(f'Falha ao criar o pool de conexão Redis: {e}')


async def check_redis_connection():
    """
    Uma função async separada para testar a conexão (ex: na inicialização do app).
    """
    if not client:
        print('Cliente Redis não foi inicializado.')
        return False
    try:
        # client.ping() agora é async e precisa de 'await'
        await client.ping()
        print(f'Conexão com Redis (ping) bem-sucedida em: {REDIS_URL}')
        return True
    except redis.exceptions.ConnectionError as e:
        print(f'Falha ao conectar (ping) ao Redis em {REDIS_URL}: {e}')

        return False


# Você exporta o 'client' (o pool) e a função de checagem.
__all__ = ['client', 'check_redis_connection']
