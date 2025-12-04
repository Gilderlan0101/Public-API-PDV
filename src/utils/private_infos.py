import re
from functools import wraps

regex_email = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
regex_cpf = r'^(\d{3}\.\d{3}\.\d{3}\-\d{2}|\d{11})$'


def private_data_output(function):
    """Mascara emails antes de executar a função."""

    @wraps(function)
    def wrapper(*args, **kwargs):
        new_args = list(args)

        for i, value in enumerate(new_args):

            # EMAIL
            if isinstance(value, str) and re.fullmatch(regex_email, value):
                new_args[i] = mask_email(value)
                continue

            # CPF
            elif isinstance(value, int) or isinstance(value, str):
                new_value = str(value)
                if re.fullmatch(regex_cpf, new_value):
                    new_args[i] = mask_cpf(new_value)
                    continue

        return function(*new_args, **kwargs)

    return wrapper


# Cria uma mascara para emails
def mask_email(value: str) -> str:
    """Mascara o email de forma inteligente preservando parte do nome e domínio."""
    if not value or '@' not in value:
        return value

    try:
        local_part, domain = value.split('@')

        # Caso email muito curto
        if len(local_part) <= 2:
            return f"{local_part}@{'*' * len(domain)}"

        # Preserva primeiro e último caractere do local part
        masked_local = (
            f"{local_part[0]}{'*' * (len(local_part) - 2)}{local_part[-1]}"
        )

        # Mascara o domínio parcialmente
        domain_parts = domain.split('.')
        if len(domain_parts) >= 2:
            masked_domain = (
                f"{'*' * len(domain_parts[0])}.{'.'.join(domain_parts[1:])}"
            )
        else:
            masked_domain = '*' * len(domain)

        return f'{masked_local}@{masked_domain}'

    except (ValueError, IndexError):
        return '*' * len(value) if value else value


def mask_cpf(value: str) -> str:
    """Retorna o CPF mascarado, mantendo os 3 primeiros e 2 últimos dígitos."""

    # Remove caracteres não numéricos
    digits = ''.join(filter(str.isdigit, value))

    if len(digits) != 11:
        raise ValueError('CPF inválido: deve conter 11 dígitos.')

    # Mantém XXX.XXX.XXX-XX -> mascara para XXX.***.***-Xreturn f"{digits[:3]}.***.***-{digits[-2:]}"
    return digits[:3] + '***' + '***' + digits[-2:]


def mask_password(value: str) -> str:
    """Mascara senha no teminal ou log de sevidores"""

    width_password = len(value)
    password = ''
    for i in range(width_password + 1):

        password = '*' * i

    return password
