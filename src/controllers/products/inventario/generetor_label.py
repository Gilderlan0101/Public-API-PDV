import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from tortoise import fields, models
from tortoise.transactions import in_transaction

# REMOVIDA A IMPORTAÇÃO: from src.utils.sales_code_generator import lot_bar_code_size
from src.model.product import Produto
from src.model.sale import Sales
# Dependências locais (mantidas em português nos comentários)
from src.utils.get_produtos_user import get_product_by_user


@dataclass
class LabelGenerator:

    # Campos de entrada
    company_id: int
    product_id: Optional[int] = None
    product_code: Optional[str] = None

    # Campo para armazenar o produto
    _product_data: Optional[Dict[str, Any]] = field(default=None, init=False)

    # 🟢 NOVO: Função auxiliar para gerar códigos de 2, 3 ou 6 dígitos
    def _generate_random_code(self) -> str:
        """
        Gera um código aleatório de 2, 3 ou 6 dígitos (como string).
        """
        # Define as opções de comprimento para o código gerado
        size_code = [2, 3, 6]
        comprimento = random.choice(size_code)

        # O valor mínimo para N dígitos é 10^(N-1)
        min_value = 10 ** (comprimento - 1)

        # O valor máximo para N dígitos é (10^N) - 1
        max_value = (10**comprimento) - 1

        # Gera o código numérico
        codigo_numerico = random.randint(min_value, max_value)

        # Retorna o código como uma string (ex: "38", "423", "987651")
        return str(codigo_numerico)

    async def fetch_product_data(self) -> bool:
        """
        Busca o produto no banco de dados.
        """
        if not self.product_id and not self.product_code:
            return False  # Não há dados suficientes para a busca

        # Lógica de busca. Assumindo que get_product_by_user retorna um dict.
        product_selected = await get_product_by_user(
            user_id=self.company_id,
            product_id=self.product_id,
            code=self.product_code,
        )

        if product_selected:
            self._product_data = product_selected
            return True
        return False

    async def create_label_by_product(self) -> Dict[str, Any]:
        """
        create_label_by_product: Busca um produto e gera uma tag (rótulo) para ele.
        return: {
            'product_name': 'name',
            'unit_of_measurement': 'KG' | 'L' | 'UNI',
            'price': 'R$ 12.30',
            'label': 'A1B2C3'
        }
        """
        # [Comentários em Português a partir daqui]

        # 1. Busca os dados do produto. Se não foram buscados, busca agora.
        if not self._product_data:
            if not await self.fetch_product_data():
                # Lançar exceção se o produto não for encontrado
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Produto não encontrado para gerar o rótulo.',
                )

        product_data = self._product_data

        # 2. Gera um código de barras/lote aleatório (substituindo o uso da função externa)
        label_code = self._generate_random_code()

        # 3. Atualiza o campo 'label' no banco de dados
        product_db_id = product_data.get('id')

        if product_db_id:
            # 🟢 Atualiza o campo 'label' no modelo Produto
            result = await Produto.filter(
                usuario_id=self.company_id, id=product_db_id
            ).update(label=label_code)

            if result == 0:
                # Lançar exceção se a atualização falhar (ex: produto não pertence à empresa)
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Falha ao atualizar o rótulo: Produto não encontrado ou não pertence a esta empresa.',
                )
        else:
            # Lançar exceção se o ID do produto não estiver disponível no _product_data
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='ID do produto indisponível para atualização no banco de dados.',
            )

        # 4. Monta o rótulo final para retorno

        # ATENÇÃO: Assumindo que product_data é um dicionário e contém os campos necessários
        product_name = product_data.get(
            'name', 'Nome Desconhecido'
        )  # Usando 'name' (campo do DB)
        unit = product_data.get('unit', 'UNI')  # Usando 'unit' (campo do DB)
        price = product_data.get('sale_price', 0.0)

        return {
            'product_name': product_name,
            'unit_of_measurement': unit,
            'price': f'R$ {price:.2f}',  # Mantendo o formato R$ por ser padrão de venda
            'label': label_code,
        }
