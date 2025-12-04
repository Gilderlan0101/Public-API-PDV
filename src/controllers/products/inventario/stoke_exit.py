from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from tortoise.expressions import F
from tortoise.transactions import atomic

# Importações internas necessárias
from src.model.product import (  # Necessário para atualizar e arquivar
    Produto,
    ProdutoArquivado,
)
from src.model.user import Usuario  # Necessário para a busca
from src.utils.get_produtos_user import (  # Assume que deep_search retorna dados para busca
    deep_search,
)


@dataclass
class StockExit:
    """
    Classe para gerenciar a saída (baixa) de produtos do estoque.
    Inclui métodos para remover quantidade parcial ou arquivar o produto completo.
    """

    company_id: int
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    quantity_to_remove: int = field(default=0)
    detail: Optional[str] = None

    def check_fields(self) -> None:
        """Verifica campos obrigatórios e valores lógicos."""
        if not self.company_id or self.company_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='ID da empresa inválido.',
            )
        if not self.product_code and not self.product_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='É obrigatório fornecer o código OU o nome do produto.',
            )

    async def _get_product_for_exit(self) -> Optional[Produto]:
        """Busca o objeto Produto no DB pelo código ou nome."""
        # A busca por código é mais direta no TortoiseORM

        product_obj = await Produto.get_or_none(
            product_code=self.product_code, usuario_id=self.company_id
        )

        # Se a busca por código falhou, tenta usar deep_search (que é mais complexo)
        if not product_obj and self.product_name:
            # 1. Busca o nome da empresa para deep_search (para ter o target_company)
            company_owner = await Usuario.get_or_none(id=self.company_id)
            target_company_name = (
                company_owner.company_name if company_owner else None
            )

            # 2. Executa deep_search (assume que retorna Dict ou List[Dict])
            search_result = await deep_search(
                user_id=self.company_id,
                product_name=self.product_name,
                target_company=target_company_name,
            )

            # 3. Se encontrar um ID no resultado do deep_search, carrega o objeto
            if (
                search_result
                and isinstance(search_result, list)
                and search_result[0].get('id')
            ):
                product_id = search_result[0].get('id')
                product_obj = await Produto.get_or_none(
                    id=product_id, usuario_id=self.company_id
                )

        if not product_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Produto não encontrado ou não pertence a esta empresa.',
            )
        return product_obj

    # -------------------------------------------------------------
    # MÉTODO 1: Remover Quantidade (Baixa Parcial)
    # -------------------------------------------------------------
    async def remove_quantity(self) -> dict:
        """
        Remove uma quantidade específica do estoque, sem arquivar o produto.
        """
        self.check_fields()

        if self.quantity_to_remove <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='A quantidade a ser removida deve ser maior que zero.',
            )

        product = await self._get_product_for_exit()

        if (product.stock or 0) < self.quantity_to_remove:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Estoque insuficiente. Disponível: {product.stock or 0}, Solicitado: {self.quantity_to_remove}',
            )

        try:
            # 1. Atualiza o estoque usando F-expression para garantir atomicidade
            rows_updated = await Produto.filter(id=product.id).update(
                stock=F('stock') - self.quantity_to_remove,
                detail=self.detail
                or product.detail,  # Mantém ou adiciona detalhe
                atualizado_em=datetime.now(ZoneInfo('America/Sao_Paulo')),
            )

            if rows_updated > 0:
                return {
                    'message': 'Baixa de estoque parcial realizada com sucesso.',
                    'product_id': product.id,
                    'quantity_removed': self.quantity_to_remove,
                }

            raise Exception('Falha desconhecida ao atualizar o DB.')

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Erro ao dar baixa no estoque: {str(e)}',
            )

    # -------------------------------------------------------------
    # MÉTODO 2: Remover Produto Total (Arquivamento)
    # -------------------------------------------------------------
    @atomic()
    async def remove_product_total(self) -> dict:
        """
        Remove todo o estoque do produto e o move para a tabela de Arquivados.
        """
        self.check_fields()

        if not self.detail:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O campo 'detail' (motivo do arquivamento) é obrigatório para remoção total.",
            )

        product = await self._get_product_for_exit()

        # 1. Criar registro de Produto Arquivado
        try:
            await ProdutoArquivado.create(
                product_code=product.product_code,
                name=product.name,
                stock=product.stock,  # Registra o estoque restante (que será 0)
                date_expired=product.date_expired,
                cost_price=product.cost_price,
                price_uni=product.price_uni,
                sale_price=product.sale_price,
                description=self.detail,  # Usa o 'detail' como motivo do arquivamento
                usuario_id=self.company_id,
                produto_id=product.id,
            )

            # DELETANDO O PRODUTO DA LISTA DE PRODUTOS
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Erro ao registrar produto arquivado: {str(e)}',
            )

        # 2. Deletar o produto da tabela principal (Produto)
        deleted_count = await Produto.filter(id=product.id).delete()

        if deleted_count > 0:
            return {
                'message': 'Produto removido do estoque principal e arquivado com sucesso.',
                'product_id': product.id,
                'archived_detail': self.detail,
            }

        rows_deleted = await Produto.filter(
            usuario_id=self.company_id, product_code=self.product_id
        ).delete()  # <--- Use o nome do campo real

        if rows_updated:
            print('OK REMOVED')

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Falha ao deletar o produto da tabela principal.',
        )
