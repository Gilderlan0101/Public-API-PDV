from datetime import datetime

from fastapi import HTTPException


async def build_receipt(
    itens: list[dict],
    usuario,  # 🔹 CORREÇÃO: Remover type annotation específico, pode ser Usuario object ou dict
    funcionario_nome: str,
    sale_code: str,
    payment_method: str,
    valor_recebido: float | None = None,
    troco: float | None = None,
    installments: int | None = None,
    customer_id: int | None = None,
    cpf: str | None = None,
) -> dict:
    """Constrói os dados do recibo (nota fiscal simplificada)"""

    try:
        if not itens or not usuario:
            raise HTTPException(
                status_code=400,
                detail='Informações da venda incompletas (build_receipt)',
            )

        # 🔹 CORREÇÃO: Acessar atributos de forma segura, seja objeto ou dict
        def get_usuario_attr(attr, default='Não informado (build_receipt)'):
            if hasattr(usuario, attr):
                return getattr(usuario, attr, default)
            elif isinstance(usuario, dict) and attr in usuario:
                return usuario[attr]
            else:
                return default

        # Informações do cliente (caso exista)
        usuario_id = get_usuario_attr('id', 'N/A')
        cliente_info = {'Código Interno do Usuário': usuario_id}

        if customer_id:
            cliente_info['Cliente ID'] = customer_id

        # 🔹 CORREÇÃO: Calcular totais de forma segura
        total_geral = 0.0
        lucro_geral = 0.0
        venda_itens = []

        for item in itens:
            try:
                quantidade = float(item.get('quantity', 0))
                preco_total = float(item.get('total_price', 0))
                lucro_total = float(item.get('lucro_total', 0))

                # Calcular preço unitário de forma segura
                preco_unitario = (
                    preco_total / quantidade if quantidade > 0 else 0
                )

                total_geral += preco_total
                lucro_geral += lucro_total

                venda_itens.append(
                    {
                        'product_name': item.get(
                            'product_name', 'Produto não informado'
                        ),
                        'Quantidade': quantidade,
                        'Preço Unitário': f'R$ {preco_unitario:.2f}',
                        'Valor Total': f'R$ {preco_total:.2f}',
                        'Lucro Total': f'R$ {lucro_total:.2f}',
                    }
                )
            except (ValueError, TypeError, ZeroDivisionError) as e:
                print(f'Erro ao processar item: {item}, erro: {e}')
                continue

        # 🔹 CORREÇÃO: Montar endereço de forma segura
        endereco_parts = []
        for attr in [
            'street',
            'home_number',
            'city',
            'state',
            'state_registration',
        ]:
            value = get_usuario_attr(attr, '').strip()
            if value:
                endereco_parts.append(value)

        endereco = (
            ', '.join(endereco_parts) if endereco_parts else 'Não informado'
        )

        # Base do recibo
        receipt_data = {
            'Nota Fiscal': {
                'Empresa': {
                    'Razão Social': get_usuario_attr(
                        'company_name', 'Não informado'
                    ),
                    'Nome Fantasia': get_usuario_attr(
                        'trade_name', 'Não informado'
                    ),
                    'CNPJ': get_usuario_attr('cnpj', 'Não informado'),
                    'Endereço': endereco,
                    'Inscrição Estadual': get_usuario_attr(
                        'state_registration', 'Não informado'
                    ),
                    'Inscrição Municipal': get_usuario_attr(
                        'municipal_registration', 'Não informado'
                    ),
                    'Operado por': funcionario_nome
                    or get_usuario_attr('username', 'Não informado'),
                    'codigo_da_venda': sale_code or 'N/A',
                },
                'Venda': venda_itens,
                'Totais': {
                    'Valor Total Geral': f'R$ {total_geral:.2f}',
                    'Lucro Total Geral': f'R$ {lucro_geral:.2f}',
                    'Quantidade de Itens': len(venda_itens),
                },
                'Cliente': cliente_info,
                'Data': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                'Forma_de_Pagamento': payment_method.upper(),
            }
        }

        # 🔹 CORREÇÃO: Adicionar informações de pagamento de forma segura
        pagamento_info = {}
        payment_upper = payment_method.upper()

        if payment_upper == 'DINHEIRO':
            if valor_recebido is not None:
                pagamento_info[
                    'Valor Recebido'
                ] = f'R$ {float(valor_recebido):.2f}'
            else:
                pagamento_info['Valor Recebido'] = 'Não informado'

            if troco is not None:
                pagamento_info['Troco'] = f'R$ {float(troco):.2f}'
            else:
                pagamento_info['Troco'] = 'R$ 0.00'

        elif payment_upper == 'CARTAO':
            if installments:
                pagamento_info['Parcelas'] = int(installments)
            else:
                pagamento_info['Parcelas'] = 'À vista'

        elif payment_upper == 'NOTA' and customer_id:
            pagamento_info['Tipo'] = 'Venda em Nota'
            pagamento_info['Cliente ID'] = customer_id

        elif payment_upper == 'PARCIAL':
            pagamento_info['Tipo'] = 'PARCIAL'
            if cpf:
                pagamento_info['CPF Cliente'] = cpf

        # Adicionar seção de pagamento apenas se houver informações
        if pagamento_info:
            receipt_data['Nota Fiscal']['Pagamento'] = pagamento_info

        # 🔹 CORREÇÃO: Adicionar valor_recebido e troco no nível superior se necessário
        if valor_recebido is not None:
            receipt_data['Nota Fiscal']['valor_recebido'] = float(
                valor_recebido
            )
        if troco is not None:
            receipt_data['Nota Fiscal']['troco'] = float(troco)

        receipt_data['Nota Fiscal'][
            'Observações'
        ] = 'Venda registrada com sucesso no sistema PDV.'

        return receipt_data

    except HTTPException:
        raise
    except Exception as e:
        print(f'Erro detalhado ao construir recibo build_receipt: {str(e)}')
        raise HTTPException(
            status_code=500,
            detail=f'Erro interno ao gerar recibo build_receipt: {str(e)}',
        )
