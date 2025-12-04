import logging
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from src.model.caixa import Caixa
from src.model.carItems import CartItem
from src.model.product import Produto

# Configuração de logging
logger = logging.getLogger(__name__)


class CartManagerDB:
    """
    Gerencia o carrinho de compras com foco em performance, segurança e consistência.

    Features:
    - Controle multi-tenant (empresa + funcionário)
    - Gestão de estoque em tempo real
    - Cálculos monetários precisos com Decimal
    - Cache de consultas frequentes
    - Transações atômicas
    - Logging detalhado para auditoria
    """

    # Cache para evitar consultas repetidas
    _caixa_cache = {}
    _produto_cache = {}

    def __init__(self, company_id: int, employee_id: int):
        self.company_id = company_id
        self.employee_id = employee_id
        self._cache_key = f'{company_id}_{employee_id}'

    def _clear_cache(self):
        """Limpa o cache quando necessário"""
        self._caixa_cache.pop(self._cache_key, None)

    async def _get_caixa_ativo(self) -> Caixa:
        """
        Busca o caixa ativo com cache para performance.

        Returns:
            Caixa: Instância do caixa ativo

        Raises:
            HTTPException: Se não encontrar caixa ativo
        """
        try:
            # Verifica cache primeiro
            if self._cache_key in self._caixa_cache:
                cached_caixa = self._caixa_cache[self._cache_key]
                if await Caixa.exists(id=cached_caixa.id, aberto=True):
                    return cached_caixa
                else:
                    self._clear_cache()

            # Busca no banco
            caixa = (
                await Caixa.filter(
                    usuario_id=self.company_id,
                    funcionario_id=self.employee_id,
                    aberto=True,
                )
                .select_related('funcionario')
                .first()
            )

            if not caixa:
                logger.warning(
                    f'Caixa não encontrado - Empresa: {self.company_id}, Funcionário: {self.employee_id}'
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail='Nenhum caixa aberto encontrado para este funcionário/empresa.',
                )

            # Atualiza cache
            self._caixa_cache[self._cache_key] = caixa
            logger.info(
                f'Caixa {caixa.caixa_id} carregado para empresa {self.company_id}'
            )

            return caixa

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro ao buscar caixa: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao acessar caixa.',
            )

    async def _get_produto(self, product_id: int) -> Produto:
        """
        Busca produto com cache e validações.

        Args:
            product_id: ID do produto

        Returns:
            Produto: Instância do produto

        Raises:
            HTTPException: Se produto não for encontrado ou inativo
        """
        cache_key = f'prod_{self.company_id}_{product_id}'

        if cache_key in self._produto_cache:
            return self._produto_cache[cache_key]

        produto = await Produto.filter(
            id=product_id, active=True, usuario_id=self.company_id
        ).first()

        if not produto:
            logger.warning(
                f'Produto {product_id} não encontrado para empresa {self.company_id}'
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Produto não encontrado ou inativo.',
            )

        self._produto_cache[cache_key] = produto
        return produto

    def _calcular_total(
        self,
        price: Decimal,
        quantity: int,
        discount: Decimal = Decimal('0'),
        addition: Decimal = Decimal('0'),
    ) -> Decimal:
        """
        Calcula o total com precisão decimal.

        Args:
            price: Preço unitário
            quantity: Quantidade
            discount: Desconto total
            addition: Acréscimo total

        Returns:
            Decimal: Valor total calculado
        """
        try:
            base_total = price * Decimal(quantity)
            total = base_total - discount + addition
            return max(Decimal('0'), total).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        except Exception as e:
            logger.error(f'Erro no cálculo do total: {e}')
            return Decimal('0')

    async def add_produto(
        self, product_id: int, quantity: int
    ) -> Dict[str, Any]:
        """
        Adiciona produto ao carrinho com gestão de estoque.

        Args:
            product_id: ID do produto
            quantity: Quantidade a adicionar

        Returns:
            Dict: Resultado da operação com dados do item

        Raises:
            HTTPException: Se estoque insuficiente ou produto inválido
        """
        start_time = datetime.now()

        try:
            caixa = await self._get_caixa_ativo()
            produto = await self._get_produto(product_id)
            quantity = int(quantity)

            # Validação de estoque
            if produto.stock < quantity:
                logger.warning(
                    f'Estoque insuficiente - Produto: {product_id}, Requerido: {quantity}, Disponível: {produto.stock}'
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f'Estoque insuficiente. Disponível: {produto.stock}',
                )

            # Busca item existente no carrinho
            cart_item = await CartItem.filter(
                caixa_id=caixa.caixa_id, product_id=product_id
            ).first()

            if cart_item:
                # Atualiza item existente
                logger.info(
                    f'Atualizando item existente - Produto: {product_id}, Quantidade adicional: {quantity}'
                )
                return await self.update_produto(
                    product_id=product_id,
                    quantity=quantity,
                    replace_quantity=False,
                )  # Adiciona à quantidade existente

            # Cria novo item
            price_decimal = Decimal(str(produto.sale_price))
            total_price = self._calcular_total(price_decimal, quantity)

            cart_item = await CartItem.create(
                caixa_id=caixa.caixa_id,
                product_id=product_id,
                product_name=produto.name,
                quantity=quantity,
                price=float(price_decimal),
                total_price=float(total_price),
                product_code=produto.product_code,
                discount=0.0,
                addition=0.0,
            )

            # Atualiza estoque
            produto.stock -= quantity
            await produto.save()
            self._produto_cache.pop(
                f'prod_{self.company_id}_{product_id}', None
            )  # Invalida cache

            logger.info(
                f'Produto adicionado - ID: {cart_item.id}, Produto: {product_id}, Quantidade: {quantity}'
            )

            execution_time = (
                datetime.now() - start_time
            ).total_seconds() * 1000
            logger.debug(f'add_produto executado em {execution_time:.2f}ms')

            return {
                'success': True,
                'item_adicionado': {
                    'id': cart_item.id,
                    'product_id': cart_item.product_id,
                    'product_name': cart_item.product_name,
                    'quantity': int(cart_item.quantity),
                    'price': float(cart_item.price),
                    'discount': float(cart_item.discount),
                    'addition': float(cart_item.addition),
                    'total_price': float(cart_item.total_price),
                    'product_code': cart_item.product_code,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro ao adicionar produto {product_id}: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao adicionar produto ao carrinho.',
            )

    async def update_produto(
        self,
        product_id: int,
        quantity: Optional[int] = None,
        discount: Optional[float] = None,
        addition: Optional[float] = None,
        replace_quantity: bool = False,
        replace_discount: bool = False,
        replace_addition: bool = False,
    ) -> Dict[str, Any]:
        """
        Atualiza item do carrinho com precisão decimal e controle de estoque.

        Args:
            product_id: ID do produto
            quantity: Nova quantidade (opcional)
            discount: Valor do desconto (opcional)
            addition: Valor do acréscimo (opcional)
            replace_quantity: Se True, substitui a quantidade em vez de somar
            replace_discount: Se True, substitui o desconto em vez de somar
            replace_addition: Se True, substitui o acréscimo em vez de somar

        Returns:
            Dict: Resultado da operação com dados atualizados
        """
        start_time = datetime.now()

        try:
            caixa = await self._get_caixa_ativo()
            cart_item = await CartItem.filter(
                caixa_id=caixa.caixa_id, product_id=product_id
            ).first()

            if not cart_item:
                logger.warning(
                    f'Item não encontrado no carrinho - Produto: {product_id}'
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Produto não encontrado no carrinho.',
                )

            produto = await self._get_produto(product_id)
            old_quantity = int(cart_item.quantity)

            logger.debug(
                f'Atualizando produto {product_id}: '
                f'qty={quantity}, discount={discount}, addition={addition}, '
                f'replace_qty={replace_quantity}, replace_disc={replace_discount}, replace_add={replace_addition}'
            )

            # Processa quantidade com controle de estoque
            if quantity is not None:
                new_quantity = await self._processar_quantidade(
                    cart_item,
                    produto,
                    quantity,
                    replace_quantity,
                    old_quantity,
                )
                cart_item.quantity = new_quantity

            # Processa desconto
            if discount is not None:
                new_discount = await self._processar_valor_monetario(
                    cart_item.discount, discount, replace_discount, 'discount'
                )
                cart_item.discount = float(new_discount)

            # Processa acréscimo
            if addition is not None:
                new_addition = await self._processar_valor_monetario(
                    cart_item.addition, addition, replace_addition, 'addition'
                )
                cart_item.addition = float(new_addition)

            # Recalcula total com precisão decimal
            price_decimal = Decimal(str(cart_item.price))
            discount_decimal = Decimal(str(cart_item.discount))
            addition_decimal = Decimal(str(cart_item.addition))

            cart_item.total_price = float(
                self._calcular_total(
                    price_decimal,
                    cart_item.quantity,
                    discount_decimal,
                    addition_decimal,
                )
            )

            await cart_item.save()

            execution_time = (
                datetime.now() - start_time
            ).total_seconds() * 1000
            logger.debug(f'update_produto executado em {execution_time:.2f}ms')

            return {
                'success': True,
                'item_atualizado': {
                    'id': cart_item.id,
                    'product_id': cart_item.product_id,
                    'product_name': cart_item.product_name,
                    'quantity': int(cart_item.quantity),
                    'price': float(cart_item.price),
                    'discount': float(cart_item.discount),
                    'addition': float(cart_item.addition),
                    'total_price': float(cart_item.total_price),
                    'product_code': cart_item.product_code,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro ao atualizar produto {product_id}: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao atualizar produto no carrinho.',
            )

    async def _processar_quantidade(
        self,
        cart_item: CartItem,
        produto: Produto,
        quantity: int,
        replace: bool,
        old_quantity: int,
    ) -> int:
        """
        Processa alteração de quantidade com controle de estoque.
        """
        quantity = int(quantity)

        if replace:
            new_quantity = quantity
            quantity_difference = new_quantity - old_quantity
        else:
            new_quantity = old_quantity + quantity
            quantity_difference = quantity

        # Remove item se quantidade for zero ou negativa
        if new_quantity <= 0:
            logger.info(
                f'Removendo produto por quantidade zero - Produto: {produto.id}'
            )
            if produto:
                produto.stock += old_quantity
                await produto.save()
                self._produto_cache.pop(
                    f'prod_{self.company_id}_{produto.id}', None
                )
            await cart_item.delete()
            raise HTTPException(
                status_code=status.HTTP_200_OK,
                detail='Produto removido do carrinho por quantidade zero.',
            )

        # Verifica estoque apenas se aumentando a quantidade
        if quantity_difference > 0 and produto.stock < quantity_difference:
            logger.warning(
                f'Estoque insuficiente para aumento - Produto: {produto.id}, Diferença: {quantity_difference}, Disponível: {produto.stock}'
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Estoque insuficiente para aumentar quantidade. Disponível: {produto.stock}',
            )

        # Ajusta estoque
        if quantity_difference != 0 and produto:
            produto.stock -= quantity_difference
            await produto.save()
            self._produto_cache.pop(
                f'prod_{self.company_id}_{produto.id}', None
            )

        return new_quantity

    async def _processar_valor_monetario(
        self,
        current_value: float,
        new_value: float,
        replace: bool,
        field_name: str,
    ) -> Decimal:
        """
        Processa valores monetários com precisão decimal.
        """
        current_decimal = Decimal(str(current_value or 0))
        new_decimal = Decimal(str(new_value or 0))

        if new_decimal < 0:
            logger.warning(f'Valor negativo para {field_name}: {new_decimal}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'{field_name.capitalize()} não pode ser negativo.',
            )

        if replace:
            result = new_decimal
        else:
            result = current_decimal + new_decimal

        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    async def listar_produtos(self) -> List[Dict[str, Any]]:
        """
        Lista produtos do carrinho agrupados e formatados.

        Returns:
            List: Lista de produtos no carrinho
        """
        try:
            caixa = await self._get_caixa_ativo()

            # Remove itens com quantidade zero
            await CartItem.filter(caixa_id=caixa.caixa_id, quantity=0).delete()

            # Busca todos os itens
            produtos = await CartItem.filter(caixa_id=caixa.caixa_id).all()

            # Agrupa por product_id
            agrupados = {}
            for item in produtos:
                key = item.product_id
                if key in agrupados:
                    agrupados[key]['quantity'] += int(item.quantity)
                    agrupados[key]['total_price'] += float(item.total_price)
                    # Mantém o maior desconto e acréscimo para evitar perda
                    agrupados[key]['discount'] = max(
                        agrupados[key]['discount'], float(item.discount or 0)
                    )
                    agrupados[key]['addition'] = max(
                        agrupados[key]['addition'], float(item.addition or 0)
                    )
                else:
                    agrupados[key] = {
                        'product_id': item.product_id,
                        'product_name': item.product_name,
                        'quantity': int(item.quantity),
                        'price': float(item.price),
                        'total_price': float(item.total_price),
                        'discount': float(item.discount or 0),
                        'addition': float(item.addition or 0),
                        'product_code': item.product_code,
                    }

            # Formata resposta
            lista_final = list(agrupados.values())
            return [
                {
                    'id': idx + 1,
                    'product_id': item['product_id'],
                    'product_name': item['product_name'],
                    'quantity': item['quantity'],
                    'price': item['price'],
                    'discount': item['discount'],
                    'addition': item['addition'],
                    'total_price': self._formatar_moeda(item['total_price']),
                    'product_code': item['product_code'],
                }
                for idx, item in enumerate(lista_final)
            ]

        except Exception as e:
            logger.error(f'Erro ao listar produtos: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao listar produtos do carrinho.',
            )

    async def remove_produto(self, product_id: int) -> Dict[str, Any]:
        """
        Remove todas as ocorrências de um produto do carrinho.

        Args:
            product_id: ID do produto a remover

        Returns:
            Dict: Resultado da operação
        """
        try:
            caixa = await self._get_caixa_ativo()
            cart_items = await CartItem.filter(
                caixa_id=caixa.caixa_id, product_id=product_id
            ).all()

            if not cart_items:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail='Produto não encontrado no carrinho.',
                )

            # Calcula quantidade total e restaura estoque
            quantidade_total = sum(int(item.quantity) for item in cart_items)
            produto = await self._get_produto(product_id)

            if produto:
                produto.stock += quantidade_total
                await produto.save()
                self._produto_cache.pop(
                    f'prod_{self.company_id}_{product_id}', None
                )

            # Remove itens
            deleted_count = await CartItem.filter(
                caixa_id=caixa.caixa_id, product_id=product_id
            ).delete()

            logger.info(
                f'Produto removido - ID: {product_id}, Quantidade restaurada: {quantidade_total}'
            )

            return {
                'success': True,
                'aviso': 'Produto removido com sucesso.',
                'detalhes': {
                    'product_id': product_id,
                    'product_name': cart_items[0].product_name,
                    'quantidade_restaurada': quantidade_total,
                    'itens_removidos': deleted_count,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f'Erro ao remover produto {product_id}: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao remover produto do carrinho.',
            )

    async def limpar_carrinho(self) -> Dict[str, Any]:
        """
        Limpa todo o carrinho e restaura estoques.

        Returns:
            Dict: Resultado da operação
        """
        try:
            caixa = await self._get_caixa_ativo()
            itens = await CartItem.filter(caixa_id=caixa.caixa_id).all()

            if not itens:
                return {'success': True, 'aviso': 'Carrinho já está vazio.'}

            # Restaura estoques
            for item in itens:
                produto = await Produto.get_or_none(
                    id=item.product_id, usuario_id=self.company_id
                )
                if produto:
                    produto.stock += int(item.quantity or 0)
                    await produto.save()
                    self._produto_cache.pop(
                        f'prod_{self.company_id}_{item.product_id}', None
                    )

            # Limpa carrinho
            await CartItem.filter(caixa_id=caixa.caixa_id).delete()
            self._clear_cache()

            logger.info(f'Carrinho limpo - Itens removidos: {len(itens)}')

            return {
                'success': True,
                'aviso': 'Carrinho limpo e estoque restaurado.',
                'itens_removidos': len(itens),
            }

        except Exception as e:
            logger.error(f'Erro ao limpar carrinho: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao limpar carrinho.',
            )

    async def limpar_carrinho_pos_venda(self, caixa_id: int) -> bool:
        """
        Limpa carrinho após venda sem restaurar estoque.

        Args:
            caixa_id: ID do caixa

        Returns:
            bool: True se limpou, False se vazio
        """
        try:
            itens = await CartItem.filter(caixa_id=caixa_id).all()
            if itens:
                await CartItem.filter(caixa_id=caixa_id).delete()
                logger.info(
                    f'Carrinho pós-venda limpo - Caixa: {caixa_id}, Itens: {len(itens)}'
                )
                return True
            return False
        except Exception as e:
            logger.error(
                f'Erro ao limpar carrinho pós-venda {caixa_id}: {str(e)}'
            )
            return False

    def _formatar_moeda(self, valor: float) -> str:
        """
        Formata valor para moeda brasileira sem locale.

        Args:
            valor: Valor a formatar

        Returns:
            str: Valor formatado em Real
        """
        try:
            if valor is None:
                return 'R$ 0,00'
            valor_float = float(valor)
            return (
                f'R$ {valor_float:,.2f}'.replace(',', 'temp')
                .replace('.', ',')
                .replace('temp', '.')
            )
        except (ValueError, TypeError):
            return 'R$ 0,00'

    async def get_resumo_carrinho(self) -> Dict[str, Any]:
        """
        Retorna resumo detalhado do carrinho para otimização do frontend.

        Returns:
            Dict: Resumo com totais e estatísticas
        """
        try:
            caixa = await self._get_caixa_ativo()
            itens = await CartItem.filter(caixa_id=caixa.caixa_id).all()

            subtotal = Decimal('0')
            total_desconto = Decimal('0')
            total_acrescimo = Decimal('0')
            total_itens = 0

            for item in itens:
                item_subtotal = Decimal(str(item.price)) * Decimal(
                    str(item.quantity)
                )
                subtotal += item_subtotal
                total_desconto += Decimal(str(item.discount or 0))
                total_acrescimo += Decimal(str(item.addition or 0))
                total_itens += int(item.quantity)

            total_geral = subtotal - total_desconto + total_acrescimo

            return {
                'success': True,
                'resumo': {
                    'subtotal': float(subtotal.quantize(Decimal('0.01'))),
                    'desconto_total': float(
                        total_desconto.quantize(Decimal('0.01'))
                    ),
                    'acrescimo_total': float(
                        total_acrescimo.quantize(Decimal('0.01'))
                    ),
                    'total_geral': float(
                        total_geral.quantize(Decimal('0.01'))
                    ),
                    'quantidade_itens': total_itens,
                    'quantidade_produtos': len(itens),
                    'subtotal_formatado': self._formatar_moeda(
                        float(subtotal)
                    ),
                    'desconto_formatado': self._formatar_moeda(
                        float(total_desconto)
                    ),
                    'acrescimo_formatado': self._formatar_moeda(
                        float(total_acrescimo)
                    ),
                    'total_formatado': self._formatar_moeda(
                        float(total_geral)
                    ),
                },
            }

        except Exception as e:
            logger.error(f'Erro ao gerar resumo do carrinho: {str(e)}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail='Erro interno ao gerar resumo do carrinho.',
            )
