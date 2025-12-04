import os
from typing import Any, Dict

from dotenv import load_dotenv
from tortoise import Tortoise
from tortoise.exceptions import ConfigurationError, DBConnectionError

# LOGS
from src.logs.infos import LOGGER

# Carregar variáveis de ambiente
load_dotenv()


def get_mysql_config() -> Dict[str, Any]:
    """
    Retorna a configuração completa para MySQL/MariaDB.

    Busca credenciais específicas para "production" ou "development"
    baseadas na variável ENVIRONMENT.
    """

    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').upper()

    if ENVIRONMENT == 'PRODUCTION':
        # Para ambiente de Produção: espera as variáveis padrão sem sufixo
        LOGGER.info(
            '🛠️ Modo PRODUCTION: Usando credenciais de Deploy (remotas).'
        )
        DB_USER = os.getenv('DB_USER')
        DB_PASS = os.getenv('DB_PASSWORD')
        DB_HOST = os.getenv('DB_HOST')
        DB_PORT = os.getenv('DB_PORT', '3306')
        DB_NAME = os.getenv('DB_NAME')
    else:
        # Para Desenvolvimento: usa credenciais de desenvolvimento
        LOGGER.info('🛠️ Modo DEVELOPMENT: Usando credenciais locais.')
        DB_USER = os.getenv('DB_USER_DEV_LOCAL', 'root')  # Valor padrão
        DB_PASS = os.getenv('DB_PASSWORD_DEV_LOCAL', '')  # Valor padrão
        DB_HOST = os.getenv('DB_HOST_DEV_LOCAL', 'localhost')  # Valor padrão
        DB_PORT = os.getenv('DB_PORT_DEV_LOCAL', '3306')  # Valor padrão
        DB_NAME = os.getenv(
            'DB_NAME_DEV_LOCAL', 'nahtec_pdv_dev'
        )  # Valor padrão

    # Log das credenciais (sem senha por segurança)
    LOGGER.info(
        f'📊 Config DB - Host: {DB_HOST}:{DB_PORT}, DB: {DB_NAME}, User: {DB_USER}'
    )

    # Verifica se as credenciais críticas foram encontradas
    missing_vars = []
    if not DB_USER:
        missing_vars.append('DB_USER')
    if not DB_HOST:
        missing_vars.append('DB_HOST')
    if not DB_NAME:
        missing_vars.append('DB_NAME')

    if missing_vars:
        LOGGER.error(
            f'❌ Variáveis de ambiente críticas faltando: {", ".join(missing_vars)}'
        )
        # Não quebra, apenas loga o erro

    return {
        'connections': {
            'default': {
                'engine': 'tortoise.backends.mysql',
                'credentials': {
                    'host': DB_HOST or 'localhost',
                    'port': int(DB_PORT) if DB_PORT else 3306,
                    'user': DB_USER or 'root',
                    'password': DB_PASS or '',
                    'database': DB_NAME or 'nahtec_pdv_dev',
                    'charset': 'utf8mb4',
                    'autocommit': True,
                    'minsize': 1,
                    'maxsize': 5,
                    'sql_mode': 'STRICT_TRANS_TABLES',
                    'connect_timeout': 30,  # Timeout de conexão
                },
            }
        },
        'apps': {
            'models': {
                'models': [
                    'src.model.user',
                    'src.model.employee',
                    'src.model.customers',
                    'src.model.caixa',
                    'src.model.cashmovement',
                    'src.model.sale',
                    'src.model.partial',
                    'src.model.carItems',
                    'src.model.product',
                    'src.model.fornecedor',
                    'src.model.membros',
                    'src.model.cnpjCache',
                    'src.model.tickets',
                    'src.model.delivery',
                    'src.model.pix',
                ],
                'default_connection': 'default',
            }
        },
        'use_tz': True,
        'timezone': 'America/Sao_Paulo',
    }


# A variável global TORTOISE_ORM é a configuração que o Main.py irá importar.
TORTOISE_ORM = get_mysql_config()

# =========================================================================
# FUNÇÕES DE CICLO DE VIDA (COM MELHORIAS)
# =========================================================================


async def init_database() -> bool:
    """Inicializa o Tortoise ORM com a configuração MySQL/MariaDB."""

    engine_name = TORTOISE_ORM['connections']['default']['engine'].split('.')[
        -1
    ]

    try:
        LOGGER.info(f'🔧 Configurando banco: {engine_name}')
        LOGGER.info(
            f"📋 Modelos carregados: {len(TORTOISE_ORM['apps']['models']['models'])}"
        )

        await Tortoise.init(config=TORTOISE_ORM)
        LOGGER.info('✅ Tortoise ORM inicializado!')

        # Testa a conexão antes de criar schemas
        try:
            await Tortoise.get_connection('default').execute_query('SELECT 1')
            LOGGER.info('✅ Conexão com MySQL verificada!')
        except Exception as e:
            LOGGER.error(f'❌ Falha ao testar conexão MySQL: {e}')
            return False

        # Cria as tabelas se não existirem
        await Tortoise.generate_schemas()
        LOGGER.info('✅ Tabelas criadas/verificadas!')

        print_database_info()
        return True

    except DBConnectionError as e:
        # Erro de conexão real (servidor MySQL não está rodando, credenciais erradas)
        LOGGER.error(f'❌ Falha ao conectar ao banco de dados MySQL: {e}')

        # Log mais detalhado para debugging
        creds = TORTOISE_ORM['connections']['default']['credentials']
        LOGGER.error(
            f'🔍 Tentando conectar em: {creds["host"]}:{creds["port"]}, DB: {creds["database"]}, User: {creds["user"]}'
        )

        return False
    except ConfigurationError as e:
        LOGGER.error(f'❌ Erro de configuração do Tortoise: {e}')
        return False
    except Exception as e:
        LOGGER.error(f'❌ Erro inesperado ao inicializar banco: {e}')
        return False


async def close_database():
    """Fecha as conexões do banco"""
    try:
        await Tortoise.close_connections()
        LOGGER.info('✅ Conexões do banco fechadas!')
    except Exception as e:
        LOGGER.warning(f'⚠️ Aviso ao fechar conexões: {e}')


def print_database_info():
    """Exibe informações de conexão do DB para o log (apenas MySQL/MariaDB)."""
    conn_config = TORTOISE_ORM['connections']['default']
    creds = conn_config['credentials']
    db_name = creds.get('database')
    db_host = creds.get('host')
    db_port = creds.get('port')

    LOGGER.info('-----------------------------------------')
    LOGGER.info(f'📦 Conectado a MySQL/MariaDB:')
    LOGGER.info(f'   - Banco: {db_name}')
    LOGGER.info(f'   - Host: {db_host}:{db_port}')
    LOGGER.info(f'   - Timezone: {TORTOISE_ORM.get("timezone", "N/A")}')
    LOGGER.info('-----------------------------------------')
