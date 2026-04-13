import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.conf.database import close_database, init_database

# LOGS
from src.logs.infos import LOGGER

# Imports das rotas
# Removemos o import * de __init__ pois pode causar conflitos de nome
from src.routes import get_api_metadata, setup_routes

# Apenas para testes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    load_dotenv()

    #  Inicializa banco usando a nova configuração
    try:
        if await init_database():
            LOGGER.info('[200] Banco de dados iniciado e tabelas criadas!')
            # await create_mock_data_and_sell_all_stock()  # Descomente se necessário
        else:
            LOGGER.error('[200] Falha ao inicializar banco de dados')
            # Não levantamos erro aqui para não derrubar o server se o banco falhar momentaneamente,
            # mas em produção idealmente deve falhar.
    except Exception as e:
        LOGGER.error(f'[500] Erro crítico no banco: {e}')

    yield

    await close_database()
    LOGGER.info('[200] Banco de dados encerrado com sucesso.')


class Server:
    def __init__(self):
        os.system('clear')

        # Correção do erro "dict is not callable":
        # Verificamos se get_api_metadata é executável antes de chamar.
        # Se for um dict (erro comum de import), usamos ele direto.
        metadata = get_api_metadata
        if callable(metadata):
            metadata = metadata()

        self.api = FastAPI(**metadata, lifespan=lifespan)

        self.setup_middlewares()
        self.start_routes()

    def setup_middlewares(self):
        """Configura CORS."""
        origins = [
            'http://127.0.0.1:5000',
            'https://nahtec.com.br',
            'https://nahtec.com.br/pdv',
            '*',  # Adicionado * para facilitar desenvolvimento, remova em produção se necessário
        ]

        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
            allow_headers=['*'],
        )

    def start_routes(self):
        """Registra as rotas principais da aplicação."""
        setup_routes(self.api)

        # Import local para evitar ciclo
        from src.routes.caixa.start_router import checkout

        self.api.include_router(checkout)

        # Informações do sistema
        self.setup_system_routes()

    def setup_system_routes(self):
        """Configura rotas do sistema e health checks."""
        from datetime import datetime

        @self.api.get('/', tags=['System'])
        async def root():
            """Endpoint raiz com informações do sistema."""
            return {
                'message': ' System is run!',
                'version': '0.1.0',
                'status': 'online',
                'docs': '/docs',
                'redoc': '/redoc',
            }

        @self.api.get('/health', tags=['system'])
        async def health_check():
            """Health check da aplicação."""
            return {
                'status': 'healthy',
                'timestamp': datetime.utcnow(),
                'service': 'DevOrbit tech',
                'version': '1.0.0',
            }

        @self.api.get('/api/v1/info', tags=['System'])
        async def system_info():
            """Informações detalhadas do sistema."""
            return {
                'name': 'DevOrbit tech',
                'version': '0.1.0',
                'description': 'Sistema completo de Ponto de Venda',
                'developer': 'Gilderlan silva',
                'contact': 'contatodevorbit@gmail.com',
                'repository': 'https://github.com/Gilderlan0101/qodo-pdv',
                'endpoints': {
                    'auth': '/api/v1/auth',
                    'products': '/api/v1/produtos',
                    'sales': '/api/v1/carrinho',
                    'dashboard': '/api/v1/dashboard',
                    'payments': '/api/v1/pagamentos',
                },
            }

    def run(self, host: str = '0.0.0.0', port: int = 8000):
        """Inicia o servidor Uvicorn."""

        environment = os.getenv('ENVIRONMENT', 'development')

        # Configurações básicas do servidor
        # CORREÇÃO: 'server' alterado para 'app' e adicionado 'port'
        start = {
            'development': {
                'app': 'Main:app',  # Uvicorn espera 'app', não 'server'
                'host': host,
                'port': port,
                'reload': True,
                'log_level': 'info',
                'access_log': True,
                'use_colors': True,
            },
            'production': {
                'app': 'Main:app',
                'host': host,
                'port': port,
                'reload': False,
                'log_level': 'warning',
                'workers': int(os.getenv('WORKERS', 4)),
            },
        }

        if environment == 'development':
            LOGGER.info('Modo: Desenvolvimento ATIVO')
            # CORREÇÃO: Adicionado ** para desempacotar o dicionário
            uvicorn.run(**start.get('development'))   # type:ignore
        else:
            LOGGER.info('Modo: Produção ATIVO')
            # CORREÇÃO: Adicionado ** para desempacotar o dicionário
            uvicorn.run(**start.get('production'))   # type:ignore


# Instância global do app
app = Server().api


def main():
    """
    Função principal para executar o servidor Qodo PDV.
    """
    LOGGER.info('-' * 60)
    LOGGER.info(' Iniciando Qodo PDV Server...')
    LOGGER.info(' Sistema de Ponto de Venda - Qodo Tech')
    LOGGER.info(' API disponível em: http://0.0.0.0:8000')
    LOGGER.info(' Documentação: http://0.0.0.0:8000/docs')
    LOGGER.info(' Redoc: http://0.0.0.0:8000/redoc')
    LOGGER.info('  Health Check: http://0.0.0.0:8000/health')
    LOGGER.info('-' * 60)

    try:
        server = Server()
        server.run()
    except KeyboardInterrupt:
        LOGGER.info('\n🛑 Servidor interrompido pelo usuário')
    except Exception as e:
        print(f'|:500:| Erro ao iniciar servidor: {e}')
        LOGGER.error(f'Erro ao iniciar servidor: {e}')


if __name__ == '__main__':
    main()
