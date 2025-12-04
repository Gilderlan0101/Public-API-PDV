import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv
from fastapi import HTTPException, status
from pydantic import BaseModel, constr, validator

from src.model.pix import Pix
from src.schemas.payments.accounts_pix import PixAccountResponse

# Configuração de logging
logger = logging.getLogger(__name__)

load_dotenv()

# Constantes
MIN_NAME_SIZE = 10
MIN_CITY_SIZE = 5
PIX_API_URL = 'https://gerarqrcodepix.com.br/api/v1'
VALID_PIX_TYPES = {'qr', 'br'}


class PixCreateRequest(BaseModel):
    """Schema para criação de PIX"""

    full_name: constr(min_length=MIN_NAME_SIZE, max_length=90)
    city: constr(min_length=MIN_CITY_SIZE, max_length=90)
    key_pix: str
    value: float = 1.00  # Valor padrão
    type_exit: str = 'qr'

    @validator('full_name')
    def validate_full_name(cls, v):
        # Remove espaços extras e valida se tem apenas letras e espaços
        v = ' '.join(v.split())  # Normaliza espaços
        if not all(c.isalpha() or c.isspace() for c in v):
            raise ValueError('Nome deve conter apenas letras e espaços')
        if len(v.replace(' ', '')) < MIN_NAME_SIZE:
            raise ValueError(
                f'Nome deve ter pelo menos {MIN_NAME_SIZE} caracteres (sem espaços)'
            )
        return v.title()

    @validator('key_pix')
    def validate_key_pix(cls, v):
        if not v or v.strip() == '':
            raise ValueError('Chave PIX é obrigatória')

        v = v.strip()

        # Validação básica de formato de chave PIX
        if len(v) < 5:
            raise ValueError('Chave PIX muito curta (mínimo 5 caracteres)')

        # Validações específicas por tipo
        # CPF (11 dígitos)
        if v.isdigit() and len(v) == 11:
            return v

        # CNPJ (14 dígitos)
        if v.isdigit() and len(v) == 14:
            return v

        # Email
        if '@' in v and '.' in v:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if re.match(email_pattern, v):
                return v

        # Telefone (com ou sem DDI)
        phone_pattern = r'^(\+55)?\s?(\d{2})?\s?9?\d{4}[-.\s]?\d{4}$'
        if re.match(
            phone_pattern, v.replace(' ', '').replace('-', '').replace('.', '')
        ):
            return v

        # Chave aleatória (UUID ou similar)
        if len(v) >= 8 and any(c.isalpha() for c in v):
            return v

        raise ValueError(
            'Chave PIX inválida. Use CPF, CNPJ, email, telefone ou chave aleatória'
        )

    @validator('value')
    def validate_value(cls, v):
        if v <= 0:
            raise ValueError('Valor deve ser maior que zero')
        if v > 1000000:  # Limite de 1 milhão
            raise ValueError('Valor muito alto (máximo R$ 1.000.000,00)')
        return round(v, 2)

    @validator('type_exit')
    def validate_type_exit(cls, v):
        if v not in VALID_PIX_TYPES:
            raise ValueError(
                f'Tipo de saída deve ser: {", ".join(VALID_PIX_TYPES)}'
            )
        return v


class GenerateQRCodeFor(BaseModel):
    """Schema para geração de QR Code"""

    value: float
    type_exit: str = 'qr'

    @validator('value')
    def validate_value(cls, v):
        if v <= 0:
            raise ValueError('Valor deve ser maior que zero')
        if v > 1000000:
            raise ValueError('Valor muito alto')
        return round(v, 2)

    @validator('type_exit')
    def validate_type_exit(cls, v):
        if v not in VALID_PIX_TYPES:
            raise ValueError(
                f'Tipo de saída deve ser: {", ".join(VALID_PIX_TYPES)}'
            )
        return v


class PixQRCodeResponse(BaseModel):
    """Response para geração de QR Code"""

    success: bool
    qr_code_file: Optional[str] = None
    br_code: Optional[str] = None
    message: str
    transaction_data: Optional[Dict] = None


class SelectAccount(BaseModel):
    """Schema para seleção de conta"""

    select: int


class PixService:
    """
    Service para gerenciamento de operações PIX
    """

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.selected_account_key = None

    async def _validate_pix_data(self, pix_data: PixCreateRequest) -> bool:
        """
        Valida dados do PIX antes do processamento
        """
        try:
            # Verifica se usuário já tem PIX com mesma chave ativa
            existing_pix = await Pix.filter(
                usuario_id=self.user_id,
                key_pix=pix_data.key_pix,
                is_active=True,
            ).first()

            if existing_pix:
                logger.warning(
                    f'Usuário {self.user_id} tentou cadastrar chave PIX duplicada: {pix_data.key_pix}'
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail='Chave PIX já cadastrada para este usuário',
                )

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro na validação PIX: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno na validação dos dados',
            )

    async def create_pix_account(self, pix_data: PixCreateRequest) -> Pix:
        """
        Cria uma nova conta PIX para o usuário - VERSÃO CORRIGIDA
        """
        try:
            # 1. Valida os dados
            await self._validate_pix_data(pix_data)

            # 2. Cria o objeto Pix - FORMA CORRETA
            pix_account = Pix(
                full_name=pix_data.full_name,
                city=pix_data.city,
                key_pix=pix_data.key_pix,
                usuario_id=self.user_id,
                is_active=True,
            )

            # 3. Salva no banco
            await pix_account.save()

            # 4. Recarrega do banco para garantir que tem o ID
            await pix_account.refresh_from_db()

            logger.info(
                f'Conta PIX criada com sucesso para usuário {self.user_id}, ID: {pix_account.id}'
            )
            return pix_account

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro ao criar conta PIX: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Erro interno ao criar conta PIX: {str(e)}',
            )

    async def generate_qr_code(
        self, pix_data: GenerateQRCodeFor
    ) -> PixQRCodeResponse:
        """
        Gera QR Code PIX dinâmico
        """
        try:
            # Obtém a conta selecionada
            # await self._get_selected_account_key() <- Futuramente usaremos este metodo
            selected_key = await self._get_selected_account_key()

            if not selected_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Nenhuma conta PIX selecionada. Selecione uma conta primeiro.',
                )

            # Obtém os dados da conta selecionada
            selected_account = await Pix.filter(
                usuario_id=self.user_id, key_pix=selected_key, is_active=True
            ).first()

            if not selected_account:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Conta PIX selecionada não encontrada',
                )

            # Parâmetros para a API
            params = {
                'nome': selected_account.full_name,
                'cidade': selected_account.city,
                'chave': selected_key,
                'valor': f'{pix_data.value:.2f}',
                'saida': pix_data.type_exit,
            }

            logger.info(
                f'Gerando QR Code PIX para usuário {self.user_id}, valor: R$ {pix_data.value:.2f}'
            )

            # Requisição para API externa
            response = requests.get(
                PIX_API_URL,
                params=params,
                timeout=30,
                headers={'User-Agent': 'PIX-Service/1.0'},
            )

            if response.status_code != 200:
                logger.error(
                    f'API PIX retornou erro: {response.status_code} - {response.text}'
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail='Serviço de QR Code indisponível',
                )

            # Processa resposta baseada no tipo de saída
            if pix_data.type_exit == 'qr':
                from datetime import datetime

                # Cria diretório se não existir
                os.makedirs('static/qrcodes', exist_ok=True)

                # Gera nome do arquivo
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'qrcode_{self.user_id}_{timestamp}.png'
                filepath = f'static/qrcodes/{filename}'

                # Salva imagem
                with open(filepath, 'wb') as f:
                    f.write(response.content)

                logger.info(f'QR Code gerado: {filename}')

                return PixQRCodeResponse(
                    success=True,
                    qr_code_file=f'/qrcode-file/{filename}',
                    message='QR Code gerado com sucesso',
                    transaction_data={
                        'value': pix_data.value,
                        'receiver': selected_account.full_name,
                        'timestamp': timestamp,
                        'key_pix': selected_key,
                    },
                )

            else:  # type_exit == 'br'
                br_code = response.text.strip()

                return PixQRCodeResponse(
                    success=True,
                    br_code=br_code,
                    message='Código BR PIX gerado com sucesso',
                    transaction_data={
                        'value': pix_data.value,
                        'receiver': selected_account.full_name,
                        'key_pix': selected_key,
                    },
                )

        except requests.exceptions.Timeout:
            logger.error('Timeout na geração do QR Code PIX')
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail='Tempo limite excedido na geração do QR Code',
            )
        except requests.exceptions.ConnectionError:
            logger.error('Erro de conexão na API PIX')
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Serviço de PIX indisponível',
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro inesperado na geração QR Code: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno na geração do QR Code',
            )

    async def get_user_pix_accounts(self) -> List[PixAccountResponse]:
        """
        Retorna todas as contas PIX ativas do usuário - VERSÃO CORRIGIDA
        """
        try:
            # Busca as contas no banco
            accounts = await Pix.filter(
                usuario_id=self.user_id, is_active=True
            ).order_by('-created_at')

            logger.info(
                f'Encontradas {len(accounts)} contas PIX para usuário {self.user_id}'
            )

            # Converte cada objeto Pix para PixAccountResponse
            result = []
            for account in accounts:
                # Log para debug
                logger.debug(
                    f'Conta PIX - ID: {account.id}, Chave: {account.key_pix}, Nome: {account.full_name}'
                )

                # Converte o objeto Tortoise para Pydantic
                account_data = PixAccountResponse(
                    id=account.id,
                    full_name=account.full_name,
                    city=account.city,
                    key_pix=account.key_pix,
                    usuario_id=account.usuario_id,
                    is_active=account.is_active,
                    created_at=account.created_at,
                    updated_at=account.updated_at,
                )
                result.append(account_data)

            return result

        except Exception as e:
            logger.error(f'Erro ao buscar contas PIX: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao buscar contas PIX',
            )

    async def deactivate_pix_account(self, pix_id: int) -> bool:
        """
        Desativa uma conta PIX
        """
        try:
            pix_account = await Pix.filter(
                id=pix_id, usuario_id=self.user_id
            ).first()

            if not pix_account:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Conta PIX não encontrada',
                )

            if not pix_account.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Conta PIX já está desativada',
                )

            pix_account.is_active = False
            await pix_account.save()

            # Se a conta desativada era a selecionada, limpa a seleção
            if self.selected_account_key == pix_account.key_pix:
                self.selected_account_key = None
                # Remove do environment também
                if 'KEY_PIX_ID' in os.environ:
                    del os.environ['KEY_PIX_ID']

            logger.info(
                f'Conta PIX {pix_id} desativada para usuário {self.user_id}'
            )
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro ao desativar conta PIX: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao desativar conta PIX',
            )

    async def select_account_default(self, select_an_account_id: int) -> str:
        """
        Seleciona uma conta PIX como padrão
        """
        try:
            # Busca a conta específica
            selected_account = await Pix.filter(
                usuario_id=self.user_id,
                id=select_an_account_id,
                is_active=True,
            ).first()

            if not selected_account:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Conta PIX não encontrada ou não está ativa',
                )

            # Armazena a chave selecionada
            self.selected_account_key = selected_account.key_pix

            # Armazena no environment para persistência (em produção use Redis ou DB)
            os.environ['KEY_PIX_ID'] = str(select_an_account_id)

            logger.info(
                f'Conta PIX {select_an_account_id} selecionada como padrão para usuário {self.user_id}'
            )
            return self.selected_account_key

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro ao selecionar conta padrão: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao selecionar conta',
            )

    async def _get_selected_account_key(self) -> Optional[str]:
        """
        Obtém a chave da conta selecionada - VERSÃO CORRIGIDA
        """
        try:
            # Tenta obter do environment primeiro
            account_id_str = os.getenv('KEY_PIX_ID')

            if account_id_str:
                account_id = int(account_id_str)
                # Busca diretamente no modelo Pix, não no PixAccountResponse
                account = await Pix.filter(
                    usuario_id=self.user_id, id=account_id, is_active=True
                ).first()
                if account:
                    self.selected_account_key = account.key_pix
                    return self.selected_account_key

            # Se não encontrou no environment, busca a primeira conta ativa DIRETAMENTE no modelo Pix
            accounts = await Pix.filter(
                usuario_id=self.user_id, is_active=True
            ).order_by('-created_at')

            if accounts:
                self.selected_account_key = accounts[0].key_pix
                # Salva no environment para próxima vez
                os.environ['KEY_PIX_ID'] = str(accounts[0].id)
                return self.selected_account_key

            return None

        except Exception as e:
            logger.error(f'Erro ao obter conta selecionada: {str(e)}')
            return None

    def get_selected_account(self) -> Optional[str]:
        """
        Retorna a conta atualmente selecionada sem fazer nova consulta
        """
        return self.selected_account_key

    async def clear_selected_account(self) -> None:
        """
        Limpa a conta selecionada
        """
        self.selected_account_key = None
        if 'KEY_PIX_ID' in os.environ:
            del os.environ['KEY_PIX_ID']
