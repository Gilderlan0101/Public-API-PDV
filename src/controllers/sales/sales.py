from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from src.controllers.sales.receipt_build import build_receipt
from src.model.customers import Customer
from src.model.employee import Employees
from src.model.product import Produto
from src.model.sale import Sales
from src.model.user import Usuario
from src.utils.get_produtos_user import get_product_by_user
from src.utils.payments_config import VALID_PAYMENT_METHODS


@dataclass
class Checkout:
    """
    Classe para processar vendas: atualizar estoque, registrar venda e gerar nota fiscal.
    """

    user_id: int = field(default=0)
    product_name: str = field(default='')
    produto_id: int = field(default=0)
    quantity: int = field(default=0)
    payment_method: str = field(default='')
    total_price: float = field(default=0.0)
    lucro_total: float = field(default=0.0)
    cpf: Optional[str] = field(default=None)
    funcionario_id: Optional[int] = field(default=None)
    funcionario_nome: Optional[str] = field(default=None)
    sale_code: Optional[str] = field(default=None)
    venda: Optional[Sales] = field(default=None)
    usuario: Optional[Usuario] = field(default=None)
    customer_id: Optional[int] = field(default=None)
    installments: Optional[int] = field(default=None)
    valor_recebido: Optional[float] = field(default=None)
    troco: Optional[float] = field(default=None)

    def __post_init__(self):
        # 🔹 CORREÇÃO: Usar a variável valid_methods que foi definida
        valid_methods = VALID_PAYMENT_METHODS + ['PARCIAL']
        if (
            self.payment_method
            and self.payment_method.upper() not in valid_methods
        ):
            raise ValueError('Forma de pagamento inválida')
        self.status = False
        self._receipt_data = None

    def _set_receipt_data(self, itens: list[dict]):
        """Setter para os dados do recibo"""
        self._receipt_data = itens

    @property
    def receipt_data(self) -> Optional[list[dict]]:
        """Property para acessar os dados do recibo"""
        return self._receipt_data

    # 🔹 CORREÇÃO: Adicionar self como primeiro parâmetro do método
    async def get_product_by_user(
        self,
        user_id: int,
        code: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Produto]:
        """Busca produto pelo usuário, código ou nome - versão mais flexível e eficiente"""

        try:
            from tortoise.expressions import Q

            if not code and not name:
                return None

            # Cria a consulta inicial para o usuário
            query = Q(usuario_id=user_id)

            # Adiciona a lógica de busca por OR
            search_terms = Q()

            if code:
                code_clean = str(code).strip().upper()
                code_no_spaces = code_clean.replace(' ', '')

                search_terms |= Q(product_code=code_clean)
                search_terms |= Q(product_code__icontains=code_clean)

                # Adiciona a busca sem espaços se for diferente
                if code_no_spaces != code_clean:
                    search_terms |= Q(product_code=code_no_spaces)

            if name:
                name_clean = name.strip().upper()
                search_terms |= Q(name__icontains=name_clean)

            # Executa a busca combinando todas as condições com AND
            # O AND é implícito ao passar múltiplos Q objects no filter
            product = await Produto.filter(query, search_terms).first()

            if not product:
                print(
                    f'❌ Nenhum produto encontrado para o usuário {user_id} com os termos fornecidos.'
                )

            return product

        except Exception as e:
            print(f'❌ Erro na busca do produto: {e}')
            return None

    async def process_sale(
        self,
        current_user: Usuario,
        product_code: str,
        quantity: int,
        payment_method: str,
        funcionario_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        installments: Optional[int] = None,
        valor_recebido: Optional[float] = None,
        sale_code: Optional[str] = None,
        troco: Optional[float] = None,
    ) -> Tuple[dict, bool]:
        """Processa uma venda completa"""
        try:
            # 🔹 CORREÇÃO: Validar parâmetros obrigatórios
            if not product_code or not quantity or not payment_method:
                raise HTTPException(
                    status_code=400,
                    detail='Código do produto, quantidade e forma de pagamento são obrigatórios',
                )

            # Define admin_user e operador
            admin_user = current_user
            operador_id = funcionario_id
            operador_nome = getattr(
                current_user, 'username', str(current_user)
            )

            # Se current_user for funcionário, pega o admin dono
            funcionario_logado = await Employees.filter(
                id=current_user.id
            ).first()
            if funcionario_logado and funcionario_logado.usuario_id:
                admin_user = await Usuario.get(
                    id=funcionario_logado.usuario_id
                )
                operador_id = funcionario_logado.id
                operador_nome = funcionario_logado.nome

            # Se foi passado funcionario_id (venda feita por admin para funcionário)
            if funcionario_id:
                func_extra = await Employees.filter(
                    id=funcionario_id,
                    usuario_id=admin_user.id,
                ).first()
                if func_extra:
                    operador_id = func_extra.id
                    operador_nome = func_extra.nome

            self.funcionario_id = operador_id
            self.funcionario_nome = operador_nome
            self.user_id = admin_user.id
            self.payment_method = payment_method.upper()
            self.customer_id = customer_id
            self.installments = installments
            self.valor_recebido = valor_recebido
            self.troco = troco
            self.sale_code = sale_code

            if not product_code or not quantity or not payment_method:
                raise HTTPException(
                    status_code=400,
                    detail='Código do produto, quantidade e forma de pagamento são obrigatórios',
                )

            from tortoise import transactions

            @transactions.atomic()
            async def process_transaction():
                nonlocal product

            # Buscar produto dentro da transação
            product = await self.get_product_by_user(
                user_id=self.user_id, code=product_code.strip()
            )

            if not product:
                raise HTTPException(
                    status_code=404, detail='Produto não encontrado'
                )

                # 🔹 CORREÇÃO: Converter para int para comparação segura
                stock_int = int(product.stock) if product.stock else 0
                quantity_int = int(quantity)

                if stock_int < quantity_int:
                    self.status = False
                    raise HTTPException(
                        status_code=400,
                        detail=f'Estoque insuficiente. Disponível: {stock_int}, Solicitado: {quantity_int}',
                    )

                # Atualiza estoque
                product.stock = stock_int - quantity_int
                product.atualizado_em = datetime.now()
                await product.save(using_db=connection)

                # 🔹 CORREÇÃO: Converter preços para float de forma segura
                sale_price = (
                    float(product.sale_price) if product.sale_price else 0.0
                )
                cost_price = (
                    float(product.cost_price) if product.cost_price else 0.0
                )

                # Calcula totais
                total_price = quantity_int * sale_price
                lucro_total = (sale_price - cost_price) * quantity_int

                # 🔹 CORREÇÃO: Preparar dados da venda sem 'using_db' no dicionário
                sale_data = {
                    'product_name': product.name,
                    'quantity': quantity_int,
                    'payment_method': payment_method.upper(),
                    'total_price': total_price,
                    'lucro_total': lucro_total,
                    'cost_price': cost_price,
                    'sale_code': self.sale_code,
                    'usuario_id': admin_user.id,
                    'produto_id': product.id,
                }

                # 🔹 CORREÇÃO: Adicionar campos opcionais apenas se existirem
                if self.funcionario_id:
                    sale_data['funcionario_id'] = self.funcionario_id

                if self.customer_id:
                    sale_data['customer_id'] = self.customer_id

                if self.installments:
                    sale_data['installments'] = self.installments

                if self.valor_recebido is not None:
                    sale_data['valor_recebido'] = float(self.valor_recebido)

                if self.troco is not None:
                    sale_data['troco'] = float(self.troco)

                # 🔹 CORREÇÃO: Criar venda passando connection separadamente
                self.venda = await Sales.create(
                    **sale_data, using_db=connection
                )
                self.usuario = admin_user

                # Prepara item para o recibo
                item_venda = {
                    'product_name': product.name,
                    'quantity': quantity_int,
                    'unit_price': sale_price,
                    'total_price': total_price,
                    'lucro_total': lucro_total,
                    'cost_price': cost_price,
                }

                self.status = True
                self._set_receipt_data([item_venda])

                # 🔹 CORREÇÃO: Gerar sale_code se não existir
                if not self.sale_code and self.venda:
                    self.sale_code = f'V{self.venda.id:06d}'

                # Retorna o recibo e status
                receipt = await build_receipt(
                    itens=[item_venda],
                    usuario=self.usuario,
                    funcionario_nome=self.funcionario_nome,
                    sale_code=self.sale_code,
                    payment_method=self.payment_method,
                    valor_recebido=self.valor_recebido,
                    troco=self.troco,
                    installments=self.installments,
                    customer_id=self.customer_id,
                    cpf=self.cpf,
                )

                return receipt, self.status

        except HTTPException:
            raise
        except Exception as e:
            self.status = False
            # 🔹 CORREÇÃO: Log mais detalhado do erro
            print(f'Erro detalhado no process_sale: {str(e)}')
            import traceback

            print(f'Traceback: {traceback.format_exc()}')
            raise HTTPException(
                status_code=400, detail=f'Erro ao processar venda: {str(e)}'
            )
