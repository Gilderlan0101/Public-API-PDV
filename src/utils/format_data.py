def format_currency(value: float) -> str:
    """
    Formata valor para moeda brasileira sem locale.

    Args:
        valor: Valor a formatar

    Returns:
        str: Valor formatado em Real
    """
    try:
        if value is None:
            return 'R$ 0,00'
        value_float = float(value)
        return (
            f'R$ {value_float:,.2f}'.replace(',', 'temp')
            .replace('.', ',')
            .replace('temp', '.')
        )
    except (ValueError, TypeError):
        return 'R$ 0,00'
