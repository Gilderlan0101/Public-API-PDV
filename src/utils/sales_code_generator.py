import random
import string

from tortoise.exceptions import IntegrityError

from src.model.product import Produto

"""
ATENÇÃO: 
    Este script foi desenvolvido apenas para fins de aprendizado do programador atual: Gilderlan Silva.
    Caso você não entenda o que está acontecendo aqui, relaxe: você pode substituir por .sort() ou sorted(), 
    métodos padrão do Python.
    Se quiser entender melhor o funcionamento, pesquise por: 
        'Quicksort: o que é e para que serve' 
    e depois por 
        'sort e sorted em Python'.
"""


def gerar_codigo_venda(size: int = 6) -> str:
    """Gera um código aleatório para a venda."""
    return ''.join(
        random.choices(string.ascii_uppercase + string.digits, k=size)
    )


def lot_bar_code_size(size: int = 13) -> str:
    """Gera um código aleatório para a venda."""
    return ''.join(random.choices(string.digits, k=size))


async def generator_code_to_checkout(usuario_id: int):
    """
    Gera código único de caixa APENAS para a empresa específica
    Versão otimizada para criação automática
    """
    from src.model.caixa import Caixa

    max_attempts = 50

    for attempt in range(max_attempts):
        # Gera código entre 100-999
        code = random.randint(100, 999)

        # Verifica se já existe para ESTA empresa
        exists = await Caixa.filter(
            usuario_id=usuario_id, caixa_id=code
        ).exists()
        if not exists:
            return code

    # Se não encontrou em 50 tentativas, usa fallback sequencial
    ultimo_caixa = (
        await Caixa.filter(usuario_id=usuario_id).order_by('-caixa_id').first()
    )
    if ultimo_caixa and ultimo_caixa.caixa_id:
        return ultimo_caixa.caixa_id + 1

    # Último fallback
    return random.randint(1000, 9999)


def quicksort(arr, key=lambda x: x):
    """Ordena uma lista usando quicksort."""
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if key(x) < key(pivot)]
    middle = [x for x in arr if key(x) == key(pivot)]
    right = [x for x in arr if key(x) > key(pivot)]
    return quicksort(left, key) + middle + quicksort(right, key)


async def barcode_generator(user_id: int, size: int = 13):
    """Gera códigos para produtos com lot_bar_code vazio e ordena pelo código."""

    # Busca produtos do usuário
    products = await Produto.filter(usuario_id=user_id)

    # Atualiza os que têm lot_bar_code = None
    for prod in products:
        if prod.lot_bar_code is None:
            prod.lot_bar_code = ''.join(random.choices(string.digits, k=size))
            print(prod.lot_bar_code)
            await prod.save()

    # Ordena os produtos pelo código de barras (usando quicksort)
    ordered_products = quicksort(products, key=lambda p: p.lot_bar_code)

    return ordered_products
