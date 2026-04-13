from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from tortoise.expressions import F
from tortoise.transactions import in_transaction

from src.controllers.sales.note import Note
from src.controllers.sales.sales import Checkout
from src.logs.infos import LOGGER
from src.model.caixa import Caixa
from src.model.cashmovement import CashMovement
from src.model.employee import Employees
from src.model.sale import Sales
from src.model.user import Usuario


class CashController:
    @staticmethod
    def _parse_float(value: Any) -> float:
        """
        Auxiliar para converter valores monetarios ou sujos para float de forma segura.
        """
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        try:
            clean_value = (
                str(value)
                .replace('R$', '')
                .replace('.', '')
                .replace(',', '.')
                .strip()
            )
            return float(clean_value)
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    async def open_checkout(
        employe_id: int, initial_balance: float, name: str, company_id: int
    ):
        """
        Abre um caixa existente para um funcionario, garantindo que so um fique aberto.
        """
        employee = await Employees.get_or_none(
            usuario_id=company_id, id=employe_id
        )
        if not employee:
            raise Exception(
                'Funcionario nao encontrado ou nao pertence a empresa'
            )

        caixa = await Caixa.filter(
            funcionario_id=employe_id, usuario_id=company_id
        ).first()
        if not caixa:
            raise Exception(
                f'Caixa nao encontrado para o funcionario {employee.nome}'
            )

        caixa_aberto_existente = await Caixa.filter(
            funcionario_id=employe_id, aberto=True, usuario_id=company_id
        ).first()

        if caixa_aberto_existente:
            LOGGER.info(f'Caixa ja esta aberto para {employee.nome}')
            return caixa_aberto_existente

        # Reabertura do caixa com reset de valores de fechamento
        caixa.aberto = True
        caixa.saldo_inicial = initial_balance
        caixa.saldo_atual = initial_balance
        caixa.valor_fechamento = None
        caixa.valor_sistema = None
        caixa.diferenca = None
        caixa.atualizado_em = datetime.now(ZoneInfo('America/Sao_Paulo'))

        async with in_transaction():
            await caixa.save()
            await CashMovement.create(
                tipo='ABERTURA',
                valor=initial_balance,
                descricao=f'Abertura do caixa {name}',
                caixa_id=caixa.id,
                usuario_id=company_id,
                funcionario_id=employe_id,
            )

        LOGGER.info(f'Caixa aberto para {employee.nome}: ID {caixa.caixa_id}')
        return caixa

    @staticmethod
    async def registrar_venda_caixa(
        caixa_id: int,
        venda_obj: Sales,
        valor_venda: float,
        forma_pagamento: str,
    ):
        caixa = await Caixa.get_or_none(id=caixa_id).prefetch_related(
            'usuario', 'funcionario'
        )
        if not caixa or not caixa.aberto:
            raise Exception('Caixa nao encontrado ou fechado')

        if not isinstance(venda_obj, Sales):
            raise Exception(f'Objeto de venda invalido: {type(venda_obj)}')

        valor_convertido = CashController._parse_float(valor_venda)
        caixa.saldo_atual += valor_convertido

        async with in_transaction():
            await CashMovement.create(
                tipo='ENTRADA',
                valor=valor_convertido,
                descricao=f'Venda #{venda_obj.id} - {forma_pagamento}',
                caixa=caixa,
                usuario=caixa.usuario,
                funcionario=caixa.funcionario,
                venda=venda_obj,
            )
            await caixa.save()

        return caixa

    @staticmethod
    async def get_caixa_status(user_id: int, funcionario_id: int = None):
        try:
            if funcionario_id:
                caixa_funcionario = await Caixa.filter(
                    funcionario_id=funcionario_id, aberto=True
                ).first()
                if caixa_funcionario:
                    return {
                        'aberto': True,
                        'caixa': caixa_funcionario,
                        'tipo': 'funcionario',
                        'funcionario_id': funcionario_id,
                    }

            caixa_usuario = await Caixa.filter(
                usuario_id=user_id, aberto=True
            ).first()
            if caixa_usuario:
                return {
                    'aberto': True,
                    'caixa': caixa_usuario,
                    'tipo': 'usuario',
                    'funcionario_id': caixa_usuario.funcionario_id,
                }

            return {
                'aberto': False,
                'caixa': None,
                'tipo': None,
                'funcionario_id': funcionario_id,
                'mensagem': 'Nenhum caixa aberto encontrado',
            }
        except Exception as e:
            raise Exception(f'Erro ao verificar status do caixa: {str(e)}')

    @staticmethod
    async def close_checkout(
        employe_id: int, checkout_id: int, company_id: int
    ) -> Optional[List[Dict[str, Any]]]:
        response_data = []

        checkout = await Caixa.filter(
            caixa_id=checkout_id, usuario_id=company_id
        ).first()
        if not checkout:
            return None

        try:
            # Calculo de saldo baseado no historico de movimentacoes
            movements = await CashMovement.filter(caixa_id=checkout.id).all()

            total_entries = sum(
                CashController._parse_float(m.valor)
                for m in movements
                if m.tipo in ['ENTRADA', 'ABERTURA']
            )
            total_exits = sum(
                CashController._parse_float(m.valor)
                for m in movements
                if m.tipo == 'SAIDA'
            )

            system_value = total_entries - total_exits
            closing_value = round(float(checkout.saldo_atual), 2)

            checkout.valor_fechamento = closing_value
            checkout.valor_sistema = system_value
            checkout.diferenca = closing_value - system_value
            checkout.aberto = False
            checkout.atualizado_em = datetime.now(
                ZoneInfo('America/Sao_Paulo')
            )

            closing_description = (
                f'Fechamento do caixa - Sistema: {system_value:.2f}, '
                f'Fechamento: {closing_value:.2f}, Dif: {checkout.diferenca:.2f}'
            )

            async with in_transaction():
                await checkout.save()
                await CashMovement.create(
                    tipo='FECHAMENTO',
                    valor=closing_value,
                    descricao=closing_description,
                    caixa_id=checkout.id,
                    usuario_id=checkout.usuario_id,
                    funcionario_id=checkout.funcionario_id,
                )

            response_data.append(
                {
                    'type': 'FECHAMENTO',
                    'value': closing_value,
                    'name': checkout.nome,
                    'description': closing_description,
                    'checkout_id': checkout.id,
                    'user_id': checkout.usuario_id,
                    'employe_id': checkout.funcionario_id,
                }
            )
            return response_data

        except Exception as error:
            LOGGER.error(f'Erro ao processar fechamento do caixa: {error}')
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f'Erro interno ao processar fechamento: {error}',
            )

    @staticmethod
    async def get_caixa_details(caixa_id: int) -> Dict[str, Any]:
        try:
            caixa = await Caixa.filter(id=caixa_id).first()
            if not caixa:
                return {'error': 'Caixa nao encontrado'}

            movimentacoes = await CashMovement.filter(
                caixa_id=caixa.id
            ).order_by('-criado_em')

            total_entradas = sum(
                CashController._parse_float(m.valor)
                for m in movimentacoes
                if m.tipo in ['ENTRADA', 'ABERTURA']
            )
            total_saidas = sum(
                CashController._parse_float(m.valor)
                for m in movimentacoes
                if m.tipo == 'SAIDA'
            )

            return {
                'caixa_id': caixa.id,
                'nome': caixa.nome,
                'saldo_atual': caixa.saldo_atual,
                'saldo_inicial': caixa.saldo_inicial,
                'aberto': caixa.aberto,
                'total_entradas': total_entradas,
                'total_saidas': total_saidas,
                'saldo_sistema': total_entradas - total_saidas,
                'movimentacoes': [
                    {
                        'id': mov.id,
                        'tipo': mov.tipo,
                        'valor': mov.valor,
                        'descricao': mov.descricao,
                        'data': mov.criado_em.strftime('%d/%m/%Y %H:%M'),
                    }
                    for mov in movimentacoes
                ],
            }
        except Exception as e:
            LOGGER.error(
                f'Erro ao buscar detalhes do caixa {caixa_id}: {str(e)}'
            )
            return {'error': str(e)}


class FinalizationObjcts:
    def __init__(self, checkout_instance: Checkout = None) -> None:
        self.checkout = checkout_instance
        self.dados_recibo = (
            checkout_instance.receipt_data if checkout_instance else None
        )
        self.nota_fiscal = None

    async def Updating_cash_values(self, caixa_id: int):
        """
        Atualiza valores do caixa, registra vendas e gera nota fiscal.
        """
        try:
            if not self.checkout or not self.checkout.venda:
                raise Exception('Dados de checkout ou venda ausentes')

            venda_obj = self.checkout.venda
            valor_total = 0.0

            # Processamento de itens do recibo ou fallbacks para compor o valor total
            if self.checkout.receipt_data and isinstance(
                self.checkout.receipt_data, list
            ):
                for item in self.checkout.receipt_data:
                    valor_total += CashController._parse_float(
                        item.get('total_price', 0)
                    )
            else:
                fallback = getattr(
                    self.checkout,
                    'total_price',
                    getattr(venda_obj, 'total_price', 0),
                )
                valor_total = CashController._parse_float(fallback)

            forma_pagamento = getattr(
                self.checkout,
                'payment_method',
                getattr(venda_obj, 'payment_method', 'PIX'),
            )

            caixa = await Caixa.get_or_none(id=caixa_id).prefetch_related(
                'usuario', 'funcionario'
            )
            if not caixa or not caixa.aberto:
                raise Exception(
                    'Caixa inexistente ou fechado para esta operacao'
                )

            # Atualizacao financeira do caixa e do acumulado do funcionario
            caixa.saldo_atual += valor_total

            async with in_transaction():
                await caixa.save()

                # Atualizacao do ranking de vendas do funcionario
                if caixa.funcionario and caixa.usuario:
                    await Employees.filter(
                        usuario_id=caixa.usuario.id, id=caixa.funcionario.id
                    ).update(
                        result_of_all_sales=F('result_of_all_sales')
                        + valor_total
                    )

                # Registro da movimentacao de entrada
                movimento_data = {
                    'tipo': 'ENTRADA',
                    'valor': valor_total,
                    'descricao': f'Venda #{venda_obj.id} - {forma_pagamento}',
                    'caixa_id': caixa.id,
                    'venda_id': venda_obj.id,
                    'usuario_id': caixa.usuario.id if caixa.usuario else None,
                    'funcionario_id': caixa.funcionario.id
                    if caixa.funcionario
                    else None,
                }
                await CashMovement.create(**movimento_data)

            # Resolucao de ID de usuario para emissao da nota
            final_user_id = self.checkout.user_id or venda_obj.usuario_id

            # Instanciacao e geracao da nota fiscal
            note_generator = Note(
                user_id=final_user_id,
                product_name=self.checkout.product_name,
                produto_id=self.checkout.produto_id,
                quantity=self.checkout.quantity,
                payment_method=forma_pagamento,
                total_price=valor_total,
                lucro_total=self.checkout.lucro_total,
                funcionario_id=self.checkout.funcionario_id,
                funcionario_nome=self.checkout.funcionario_nome,
                sale_code=self.checkout.sale_code,
                customer_id=self.checkout.customer_id,
                installments=self.checkout.installments,
                valor_recebido=self.checkout.valor_recebido,
                troco=self.checkout.troco,
                usuario=caixa.usuario,
            )
            note_generator._set_receipt_data(self.checkout.receipt_data)
            self.nota_fiscal = await note_generator.createNote()

            # Vinculo final da venda ao caixa
            venda_obj.caixa_id = caixa.id
            await venda_obj.save()

            return {'caixa': caixa, 'nota_fiscal': self.nota_fiscal}

        except Exception as e:
            LOGGER.error(f'Erro na finalizacao da venda: {str(e)}')
            raise Exception(f'Erro ao finalizar venda (Caixa/Nota): {str(e)}')
