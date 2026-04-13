from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

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
from src.logs.infos import LOGGER


@dataclass
class Checkout:
    """
    Classe responsavel por processar vendas: atualizacao de estoque,
    registro em banco e montagem de dados para nota fiscal/recibo.
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
        valid_methods = VALID_PAYMENT_METHODS + ['PARCIAL']
        if (
            self.payment_method
            and self.payment_method.upper() not in valid_methods
        ):
            raise ValueError('Forma de pagamento invalida')

        self.status = False
        self._receipt_data = None

    def _set_receipt_data(self, itens: list[dict]):
        """Armazena os dados processados para geracao do recibo."""
        self._receipt_data = itens

    @property
    def receipt_data(self) -> Optional[list[dict]]:
        return self._receipt_data

    async def get_product_by_user(
        self,
        user_id: int,
        code: Optional[str] = None,
        name: Optional[str] = None,
    ) -> Optional[Produto]:
        """Busca produto no catalogo do usuario utilizando codigo ou nome."""
        try:
            if not code and not name:
                return None

            # Base da query isolada para o usuario atual
            query_base = Produto.filter(usuario_id=user_id)
            search_terms = Q()

            if code:
                code_clean = str(code).strip().upper()
                code_no_spaces = code_clean.replace(' ', '')

                search_terms |= Q(product_code=code_clean)
                search_terms |= Q(product_code__icontains=code_clean)
                if code_no_spaces != code_clean:
                    search_terms |= Q(product_code=code_no_spaces)

            if name:
                name_clean = name.strip().upper()
                search_terms |= Q(name__icontains=name_clean)

            product = await query_base.filter(search_terms).first()

            if not product:
                LOGGER.warning(
                    f'Nenhum produto encontrado para o usuario {user_id} com os termos: code={code}, name={name}.'
                )

            return product

        except Exception as e:
            LOGGER.error(f'Erro na busca do produto: {e}')
            return None

    async def _resolve_operator(
        self, current_user: Usuario, override_funcionario_id: Optional[int]
    ) -> Tuple[Usuario, Optional[int], str]:
        """
        Define quem e a empresa (admin) e quem e o operador da venda.
        Trata o cenario onde um funcionario esta logado ou o admin esta
        imputando uma venda no nome de um funcionario especifico.
        """
        admin_user = current_user
        operador_id = override_funcionario_id
        operador_nome = getattr(current_user, 'username', str(current_user))

        # Caso o usuario logado seja na verdade um funcionario
        funcionario_logado = await Employees.filter(id=current_user.id).first()

        if funcionario_logado and funcionario_logado.usuario_id:
            admin_user = await Usuario.get(id=funcionario_logado.usuario_id)
            operador_id = funcionario_logado.id
            operador_nome = funcionario_logado.nome

        # Caso o admin logado esteja atribuindo a venda a um funcionario
        elif override_funcionario_id:
            func_extra = await Employees.filter(
                id=override_funcionario_id, usuario_id=admin_user.id
            ).first()
            if func_extra:
                operador_id = func_extra.id
                operador_nome = func_extra.nome

        return admin_user, operador_id, operador_nome

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
        """
        Executa o fluxo completo da venda contido em uma transacao atomica.
        """
        if not product_code or not quantity or not payment_method:
            raise HTTPException(
                status_code=400,
                detail='Codigo do produto, quantidade e forma de pagamento sao obrigatorios',
            )

        # 1. Resolucao de Permissoes e Identidades
        admin_user, op_id, op_nome = await self._resolve_operator(
            current_user, funcionario_id
        )

        self.funcionario_id = op_id
        self.funcionario_nome = op_nome
        self.user_id = admin_user.id
        self.usuario = admin_user
        self.payment_method = payment_method.upper()
        self.customer_id = customer_id
        self.installments = installments
        self.valor_recebido = valor_recebido
        self.troco = troco
        self.sale_code = sale_code

        try:
            # 2. Inicio do Bloco Transacional
            async with in_transaction():

                # Busca de Produto
                product = await self.get_product_by_user(
                    user_id=self.user_id, code=product_code.strip()
                )
                if not product:
                    raise HTTPException(
                        status_code=404, detail='Produto nao encontrado'
                    )

                stock_int = int(product.stock) if product.stock else 0
                quantity_int = int(quantity)

                # Validacao de Estoque
                if stock_int < quantity_int:
                    self.status = False
                    raise HTTPException(
                        status_code=400,
                        detail=f'Estoque insuficiente. Disponivel: {stock_int}, Solicitado: {quantity_int}',
                    )

                # Atualizacao de Estoque
                product.stock = stock_int - quantity_int
                product.atualizado_em = datetime.now(
                    ZoneInfo('America/Sao_Paulo')
                )
                await product.save()

                # Calculos Financeiros
                sale_price = (
                    float(product.sale_price) if product.sale_price else 0.0
                )
                cost_price = (
                    float(product.cost_price) if product.cost_price else 0.0
                )
                total_price = quantity_int * sale_price
                lucro_total = (sale_price - cost_price) * quantity_int

                # Preparacao dos Dados para Insercao da Venda
                sale_data = {
                    'product_name': product.name,
                    'quantity': quantity_int,
                    'payment_method': self.payment_method,
                    'total_price': total_price,
                    'lucro_total': lucro_total,
                    'cost_price': cost_price,
                    'sale_code': self.sale_code,
                    'usuario_id': admin_user.id,
                    'produto_id': product.id,
                }

                # Adicao dinamica de parametros opcionais
                opcionais = {
                    'funcionario_id': self.funcionario_id,
                    'customer_id': self.customer_id,
                    'installments': self.installments,
                    'valor_recebido': float(self.valor_recebido)
                    if self.valor_recebido is not None
                    else None,
                    'troco': float(self.troco)
                    if self.troco is not None
                    else None,
                }
                sale_data.update(
                    {k: v for k, v in opcionais.items() if v is not None}
                )

                # Registro da Venda
                self.venda = await Sales.create(**sale_data)

                # Geracao do Sale Code caso nao tenha sido injetado
                if not self.sale_code and self.venda:
                    self.sale_code = f'V{self.venda.id:06d}'

                # 3. Montagem do Recibo
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

                # Construcao final do recibo
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
            LOGGER.error(f'Erro no processamento da venda: {e}', exc_info=True)
            raise HTTPException(
                status_code=400, detail=f'Erro ao processar venda: {str(e)}'
            )
