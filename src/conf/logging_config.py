# src/core/logging_config.py
import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def setup_logging():
    """Configura o sistema de logging profissional"""

    # Criar diretório de logs se não existir
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Formatação
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    # Handler para arquivo
    file_handler = RotatingFileHandler(
        f'{log_dir}/app.log', maxBytes=10485760, backupCount=5
    )  # 10MB
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Configurar logger raiz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remover handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Adicionar novos handlers
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Silenciar logs muito verbosos
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
    logging.getLogger('tortoise').setLevel(logging.WARNING)
