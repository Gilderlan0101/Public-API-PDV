from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, status
from tortoise.expressions import F

from src.model.product import Produto
from src.model.user import Usuario
from src.utils.get_produtos_user import deep_search, get_product_by_user


@dataclass
class EntryProducts:
    """
    Classe para processar a entrada de novos produtos no estoque.
    Permite buscar e atualizar o estoque usando o nome OU o código do produto.
    """

    company_id: int
    new_stock: int
    product_name: Optional[str] = None
    product_code: Optional[str] = None
    detail: Optional[str] = None

    def check_fields(self) -> None:
        """Verifica campos obrigatórios e valores lógicos antes de iniciar a transação."""
        if not self.company_id or self.company_id <= 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='ID da empresa (company_id) é inválido ou ausente.',
            )
        if not self.product_name and not self.product_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='É obrigatório fornecer o nome OU o código do produto para a busca.',
            )
        if self.new_stock <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='A nova quantidade de estoque (new_stock) deve ser maior que zero.',
            )

    async def _find_product_id(self) -> Optional[int]:
        """
        Busca o produto no banco de dados e retorna o ID do Produto (int).
        Garante que o resultado seja padronizado, independentemente da função de busca.
        """
        # 1. Busca o nome da empresa para deep_search
        company_owner = await Usuario.filter(id=self.company_id).first()
        target_company_name = (
            company_owner.company_name
            if company_owner and company_owner.company_name
            else None
        )

        search_result = None

        try:
            # 2. Busca por Código (Mais preciso)
            if self.product_code:
                # get_product_by_user retorna um DICT (via .values())
                search_result = await get_product_by_user(
                    user_id=self.company_id, code=self.product_code
                )

                # CORREÇÃO: Se for um dict, extrai o 'id'
                if isinstance(search_result, dict) and search_result.get('id'):
                    return search_result.get('id')

            # 3. Busca por Nome (Usa deep_search, que retorna tipicamente List[Dict])
            elif self.product_name:
                # deep_search retorna uma lista de Dicts (assumindo que o primeiro é o melhor match)
                results_list = await deep_search(
                    user_id=self.company_id,
                    product_name=self.product_name,
                    target_company=target_company_name,
                )

                # CORREÇÃO: Se for uma lista de resultados e o primeiro item for um dict, extrai o 'id'
                if (
                    results_list
                    and isinstance(results_list, list)
                    and isinstance(results_list[0], dict)
                    and results_list[0].get('id')
                ):
                    return results_list[0].get('id')

            return None

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Erro interno na busca do produto: {e}',
            )

    async def update_stock(self) -> dict:
        """
        Atualiza o estoque de um produto existente, registrando uma nova entrada.
        """
        self.check_fields()

        # 1. Busca o ID do produto de forma padronizada
        product_id = await self._find_product_id()

        if not product_id:
            # Se o ID não foi encontrado/extraído em _find_product_id
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Erro: Produto não encontrado ou o ID não pôde ser determinado.',
            )

        # 2. Recarrega o objeto Produto para garantir a atualização
        # NOTA: O erro anterior '...não pôde ser carregado para atualização'
        # ocorreu porque você tentou usar get_or_none com um ID não numérico,
        # ou o ID não existia mais. Agora que temos o ID (int), a busca é simples.

        # Não precisamos carregar o objeto completo, apenas atualizar a linha com o ID
        try:
            update_fields = {'stock': F('stock') + self.new_stock}

            if self.detail:
                update_fields['detail'] = self.detail

            # 3. Executa a atualização por ID e usuário (mais seguro)
            rows_updated = await Produto.filter(
                id=product_id, usuario_id=self.company_id
            ).update(**update_fields)

            # 4. Verifica o resultado
            if rows_updated > 0:
                return {
                    'message': 'Atualização de estoque realizada com sucesso.',
                    'product_id': product_id,
                    'status_code': status.HTTP_200_OK,
                }
            else:
                # Se o produto existe mas a atualização falhou (0 linhas afetadas),
                # significa que o filtro não bateu (ID ou company_id incorretos).
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Erro: Falha ao atualizar o estoque. O produto não pertence a esta empresa ou não existe mais.',
                )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Erro interno ao finalizar a atualização do estoque: {e}',
            )
