import os
from typing import Any, Dict

from dotenv import load_dotenv
from tortoise import Tortoise
from tortoise.exceptions import ConfigurationError, DBConnectionError

# LOGS
from src.logs.infos import LOGGER

# Carregar variáveis de ambiente
load_dotenv()


def get_sqlite_config() -> Dict[str, Any]:
    """
    Retorna a configuração completa para SQLite.
    O SQLite utiliza um arquivo local, portanto simplificamos as credenciais.
    """
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development').upper()

    # Busca o nome do banco ou define o padrão
    DB_NAME = os.getenv('DB_NAME_DEV_LOCAL', 'nahtec_pdv_dev.db')

    # Garante que o nome do arquivo termine com .db para clareza
    if not DB_NAME.endswith('.db'):
        DB_NAME += '.db'
    LOGGER.info('-' * 60)
    LOGGER.info(f'🛠️ Modo {ENVIRONMENT}: Inicializando Banco SQLite.')
    LOGGER.info(f'Arquivo de Banco: {DB_NAME}')
    LOGGER.info('-' * 60)

    return {
        'connections': {'default': f'sqlite://{DB_NAME}'},
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


# Configuração global para o Tortoise
TORTOISE_ORM = get_sqlite_config()


async def init_database() -> bool:
    """Inicializa o Tortoise ORM com SQLite."""
    try:
        LOGGER.info('🔧 Configurando engine: SQLite')
        LOGGER.info('-' * 60)
        LOGGER.info(
            f"📋 Modelos carregados: {len(TORTOISE_ORM['apps']['models']['models'])}"
        )
        LOGGER.info('-' * 60)

        # Inicializa o Tortoise
        await Tortoise.init(config=TORTOISE_ORM)

        # Cria as tabelas automaticamente se não existirem
        await Tortoise.generate_schemas()
        import time

        LOGGER.info('-' * 60)
        time.sleep(3)
        LOGGER.info('[200] Tortoise ORM inicializado e tabelas verificadas!')
        os.system('clear')
        LOGGER.info('-' * 60)
        print_database_info()
        return True

    except DBConnectionError as e:
        LOGGER.info('-' * 60)
        LOGGER.error(f'Falha ao acessar o arquivo SQLite: {e}')
        return False
    except ConfigurationError as e:
        LOGGER.info('-' * 60)
        LOGGER.error(f'Erro de configuração no mapeamento dos modelos: {e}')
        return False
    except Exception as e:
        LOGGER.info('-' * 60)
        LOGGER.error(f'Erro inesperado ao inicializar banco: {e}')
        return False


async def close_database():
    """Fecha as conexões do banco."""
    try:
        await Tortoise.close_connections()
        LOGGER.info('✅ Conexões do banco fechadas!')
    except Exception as e:
        LOGGER.warning(f'⚠️ Aviso ao fechar conexões: {e}')


def print_database_info():
    """Exibe informações do SQLite para o log."""
    db_url = TORTOISE_ORM['connections']['default']

    LOGGER.info('|-----------------------------------------|')
    LOGGER.info('| [OK] Banco de Dados ATIVO: |')
    LOGGER.info(f'|   - Tipo: SQLite (Arquivo Local)|')
    LOGGER.info(f'|   - Caminho: {db_url.replace("sqlite://", "")}|')
    LOGGER.info(f'|   - Timezone: {TORTOISE_ORM.get("timezone", "N/A")} |')
    LOGGER.info('|-----------------------------------------|')
