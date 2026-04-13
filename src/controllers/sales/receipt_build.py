from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import HTTPException, status
from src.logs.infos import LOGGER


def _format_currency(value: Union[float, int, None]) -> str:
    """Auxiliar interno para formatar valores em Reais."""
    val = float(value) if value is not None else 0.0
    return f'R$ {val:.2f}'


def _get_val(obj: Any, attr: str, default: Any = 'N/A') -> Any:
    """Extrai valor de um objeto ou dicionario de forma segura."""
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


async def build_receipt(
    itens: List[Dict[str, Any]],
    usuario: Any,
    funcionario_nome: str,
    sale_code: str,
    payment_method: str,
    valor_recebido: Optional[float] = None,
    troco: Optional[float] = None,
    installments: Optional[int] = None,
    customer_id: Optional[int] = None,
    cpf: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Constroi a estrutura de dados para o recibo (Nota Fiscal simplificada).

    Esta funcao consolida informacoes da empresa, itens vendidos, calculos financeiros
    e detalhes do pagamento em um dicionario formatado para o cliente final.
    """

    if not itens or not usuario:
        LOGGER.error(
            'Tentativa de gerar recibo com itens ou usuario ausentes.'
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Informacoes de venda insuficientes para gerar o recibo.',
        )

    try:
        # 1. Processamento dos Itens da Venda
        venda_itens = []
        total_geral = 0.0
        lucro_geral = 0.0

        for item in itens:
            try:
                qty = float(item.get('quantity', 0))
                price_total = float(item.get('total_price', 0))
                profit_total = float(item.get('lucro_total', 0))

                unit_price = price_total / qty if qty > 0 else 0.0

                total_geral += price_total
                lucro_geral += profit_total

                venda_itens.append(
                    {
                        'product_name': item.get(
                            'product_name', 'Produto N/I'
                        ),
                        'Quantidade': qty,
                        'Preço Unitário': _format_currency(unit_price),
                        'Valor Total': _format_currency(price_total),
                        'Lucro Total': _format_currency(profit_total),
                    }
                )
            except (ValueError, TypeError, ZeroDivisionError) as e:
                LOGGER.warning(
                    f'Item ignorado no recibo por erro de calculo: {item} | Erro: {e}'
                )
                continue

        # 2. Montagem do Endereco da Empresa
        addr_fields = ['street', 'home_number', 'city', 'state']
        addr_parts = [
            str(_get_val(usuario, f, '')).strip() for f in addr_fields
        ]
        endereco_str = (
            ', '.join([p for p in addr_parts if p]) or 'Endereco nao informado'
        )

        # 3. Informacoes de Pagamento
        payment_upper = payment_method.upper()
        pagamento_info = {}

        if payment_upper == 'DINHEIRO':
            pagamento_info['Valor Recebido'] = (
                _format_currency(valor_recebido)
                if valor_recebido is not None
                else 'N/I'
            )
            pagamento_info['Troco'] = _format_currency(troco)
        elif payment_upper == 'CARTAO':
            pagamento_info['Parcelas'] = (
                int(installments) if installments else 'A vista'
            )
        elif payment_upper == 'NOTA':
            pagamento_info['Tipo'] = 'Venda em Nota'
            pagamento_info['Cliente ID'] = customer_id
        elif payment_upper == 'PARCIAL':
            pagamento_info['Tipo'] = 'PARCIAL'
            if cpf:
                pagamento_info['CPF Cliente'] = cpf

        # 4. Construcao do Dicionario Final (Mantendo estrutura original)
        receipt_data = {
            'Nota Fiscal': {
                'Empresa': {
                    'Razão Social': _get_val(usuario, 'company_name', 'N/A'),
                    'Nome Fantasia': _get_val(usuario, 'trade_name', 'N/A'),
                    'CNPJ': _get_val(usuario, 'cnpj', 'N/A'),
                    'Endereço': endereco_str,
                    'Inscrição Estadual': _get_val(
                        usuario, 'state_registration', 'N/I'
                    ),
                    'Inscrição Municipal': _get_val(
                        usuario, 'municipal_registration', 'N/I'
                    ),
                    'Operado por': funcionario_nome
                    or _get_val(usuario, 'username', 'N/A'),
                    'codigo_da_venda': sale_code or 'N/A',
                },
                'Venda': venda_itens,
                'Totais': {
                    'Valor Total Geral': _format_currency(total_geral),
                    'Lucro Total Geral': _format_currency(lucro_geral),
                    'Quantidade de Itens': len(venda_itens),
                },
                'Cliente': {
                    'Código Interno do Usuário': _get_val(
                        usuario, 'id', 'N/A'
                    ),
                    'Cliente ID': customer_id if customer_id else 'N/A',
                },
                'Data': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'Forma_de_Pagamento': payment_upper,
                'Observações': 'Venda registrada com sucesso no sistema PDV.',
            }
        }

        # Insercao de campos de pagamento se houver dados
        if pagamento_info:
            receipt_data['Nota Fiscal']['Pagamento'] = pagamento_info

        # Insercao de valores brutos no nivel superior da Nota para compatibilidade
        if valor_recebido is not None:
            receipt_data['Nota Fiscal']['valor_recebido'] = float(
                valor_recebido
            )
        if troco is not None:
            receipt_data['Nota Fiscal']['troco'] = float(troco)

        return receipt_data

    except Exception as e:
        LOGGER.error(
            f'Erro critico na geracao do recibo {sale_code}: {e}',
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Erro interno ao processar os dados do recibo.',
        )
