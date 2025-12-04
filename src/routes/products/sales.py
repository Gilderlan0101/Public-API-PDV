import traceback  # Importado para o tratamento de erro final
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, status

from src.auth.deps import SystemUser, get_current_user
from src.auth.deps_employes import SystemEmployees, get_current_employee
from src.controllers.caixa.cash_controller import (
    CashController,
    FinalizationObjcts,
)
from src.controllers.car.cart_control import CartManagerDB
from src.controllers.payments.partial.process_partial_payments import (
    PartialPayment,
)
from src.controllers.sales.delete_sales import delete_or_update_sale
from src.controllers.sales.note import Note
from src.controllers.sales.sales import Checkout
from src.controllers.sales.services import processar_venda_carrinho
from src.controllers.sales.validators import validating_information
from src.core.session_manager import get_session
from src.logs.infos import LOGGER
from src.model.caixa import Caixa
from src.model.employee import Employees
from src.model.user import Usuario
from src.schemas.payments.payment_methods import InputData

router = APIRouter()


@router.post('/finalizar', status_code=status.HTTP_200_OK)
async def finalizar_venda(
    payment_method: str = Body(
        ...,
        description='Forma de pagamento: dinheiro, cartão, pix, nota, parcial',
    ),
    customer_id: Optional[int] = Body(
        None, description='ID do cliente para venda em nota'
    ),
    installments: Optional[int] = Body(
        None, description='Número de parcelas para cartão'
    ),
    cpf: Optional[str] = Body(
        None, description='CPF passado dinamicamente em vendas parcias'
    ),
    valor_recebido: Optional[float] = Body(
        None, description='Valor recebido em dinheiro'
    ),
    troco: Optional[float] = Body(
        None, description='Troco para pagamento em dinheiro'
    ),
    current_user: SystemEmployees = Depends(get_current_employee),
):
    """
    Finaliza venda - para admin e funcionários.
    """
    # 1. Definição de IDs com base no usuário logado

    checkout_id = None

    try:

        empresa_id = current_user.empresa_id
        employee_id = current_user.id
        checkout_id = current_user.checkout_id

        cart = CartManagerDB(company_id=empresa_id, employee_id=employee_id)
        cart_items = await cart.listar_produtos()

        if not cart_items:
            raise HTTPException(
                status_code=400,
                detail='Carrinho vazio. Adicione produtos antes de finalizar a venda.',
            )

        # 🔹 1. Processa a Venda (Cria a instância de Checkout e a Venda no DB)
        validation_process = await processar_venda_carrinho(
            user_id=empresa_id,  # ID da Empresa/Dono (fundamental para a venda)
            cart_items=cart_items,
            payment_method=payment_method.upper(),
            employee_operator_id=employee_id,  # ID de quem operou
            customer_id=customer_id,
            installments=installments,
            cpf=cpf,
            valor_recebido=valor_recebido,
            troco=troco,
        )

        if not validation_process.get('success'):
            error_msg = (
                validation_process.get('message')
                or validation_process.get('error')
                or 'Erro ao processar venda'
            )
            raise HTTPException(status_code=400, detail=error_msg)

        validation_data = validation_process.get('data', {})
        checkout_instance: Checkout = validation_data.get('checkout_instance')

        if (
            not checkout_instance
            or not hasattr(checkout_instance, 'venda')
            or not checkout_instance.venda
        ):
            raise HTTPException(
                status_code=500,
                detail='Instância do checkout inválida ou venda não processada',
            )

        # 🔹 2. Atualiza valores do caixa (Pré-requisito para documentos fiscais)

        caixa_aberto = await CashController.get_caixa_aberto_funcionario(
            usuario_id=empresa_id, funcionario_id=employee_id
        )
        if not caixa_aberto:
            raise HTTPException(
                status_code=404,
                detail=f'Atenção: Nenhum caixa aberto encontrado para o funcionário {employee_id}',
            )

        nota_fiscal = None

        # 🚨 BLOCO TRY/EXCEPT: Trata erros APENAS na atualização pós-venda (Caixa/Nota)
        try:
            # Atualiza caixa E GERA NOTA usando a instância de Checkout
            finalizacao = FinalizationObjcts(checkout_instance)

            # O método Updating_cash_values agora retorna um dicionário com o caixa e a nota_fiscal
            resultado_final = await finalizacao.Updating_cash_values(
                checkout_id
            )

            nota_fiscal = resultado_final.get(
                'nota_fiscal'
            )  # Extrai a nota do retorno

            # Prepara resumo_venda
            sale_code = getattr(checkout_instance, 'sale_code', 'N/A')
            payment_method_final = getattr(
                checkout_instance, 'payment_method', payment_method.upper()
            )
            total_venda = int(validation_data.get('total_venda', 0))

            resumo_venda = {
                'sale_code': sale_code,
                'total_venda': total_venda,
                'payment_method': payment_method_final,
                'funcionario_operador_id': employee_id,
                'caixa_id': current_user.checkout_id,
                'customer_id': customer_id,
                'venda_id': checkout_instance.venda.id,
                'quantidade_itens': len(cart_items),
                'nota_fiscal': nota_fiscal,
            }

            # Limpa o carrinho
            await cart.limpar_carrinho_pos_venda(caixa_id=checkout_id)

            # Se tudo ocorreu, retorna sucesso
            return {'success': True, 'data': resumo_venda}

        except HTTPException as http_exc:
            # Tratamento Crucial: Propaga o erro HTTP se ele veio da finalização (ex: 404/400)
            raise http_exc

        except (ValueError, TypeError) as e:
            # Tratamento de erro específico para falha na PÓS-VENDA (Caixa ou Nota)
            print(f'Erro ao atualizar caixa ou gerar nota: {e}')

            # Recalcula dados para resumo (Venda foi salva, mas pós-venda falhou)
            total_venda = int(validation_data.get('total_venda', 0))
            resumo_venda = {
                'sale_code': getattr(checkout_instance, 'sale_code', 'N/A'),
                'total_venda': total_venda,
                'payment_method': getattr(
                    checkout_instance, 'payment_method', payment_method.upper()
                ),
                'funcionario_operador_id': employee_id,
                'caixa_atualizado': False,
                'finalizacao_erro': str(
                    e.__class__.__name__
                ),  # Erro genérico de finalização
                'customer_id': customer_id,
                'venda_id': checkout_instance.venda.id
                if checkout_instance.venda
                else None,
                'quantidade_itens': len(cart_items),
                'nota_fiscal': nota_fiscal,
            }
            # Retorna 200 indicando que a VENDA foi salva, mas houve falha na PÓS-VENDA
            LOGGER.debug(
                f'Venda finalizada, mas houve falha na atualização do caixa/geração de documento {str(e)}'
            )
            return {
                'success': True,
                'message': f'Venda finalizada, mas houve falha na atualização do caixa/geração de documento: {str(e)}',
                'data': resumo_venda,
            }

    except HTTPException as e:
        # Erros que ocorrem ANTES do bloco de finalização (ex: carrinho vazio, 403)
        raise e
    except Exception as e:
        print(f'Erro interno ao processar venda: {str(e)}')
        import traceback

        print(f'Traceback completo: {traceback.format_exc()}')
        raise HTTPException(
            status_code=500,
            detail=f'Erro interno ao processar venda: {str(e)}',
        )


@router.delete('/deleta/venda/')
async def delete_sale(
    product_id: int = Body(...),
    quantity: Optional[int] = None,
    current_user: SystemEmployees = Depends(get_current_employee),
):
    """O usuario/funcionario pode deletar uma venda ou editar uma venda realizada."""

    # Verifica se o usuário atual é um funcionário
    employee_id = current_user.employee_id

    funcionario = await Employees.filter(id=employee_id).first()

    if funcionario:
        # Se for funcionário, usa o usuario_id do funcionário (ID do admin)
        user_id_carrinho = funcionario.usuario_id
    else:
        # Se não for funcionário, é admin e usa seu próprio ID
        user_id_carrinho = current_user.id

    result = await delete_or_update_sale(
        user_id_carrinho, product_id, quantity
    )
    return result


@router.post('/pagamento-parcial')
async def payment_partial(
    data: InputData,
    current_user: SystemEmployees = Depends(get_current_employee),
):

    try:

        if not current_user.id:
            raise HTTPException(
                status_code=400, detail='Usuario não encontrado.'
            )

        partial = PartialPayment(
            payment_method=data.product_name,
            value_received=data.value_received,
            cpf=data.cpf,
            user_id=current_user.empresa_id,  # User .id ou empresa_id
        )

        result = await partial.update_value()
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Erro interno: {e}')

    except TypeError as e:
        raise HTTPException(status_code=500, detail=f'Erro interno: {e}')
