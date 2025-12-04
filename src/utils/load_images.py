# load_images.py

import os
from typing import List, Optional

from fastapi import HTTPException, status

from src.model.product import Produto
from src.utils.get_produtos_user import get_product_by_user


async def load_imgs(
    path: str, store_id: int, product_id: Optional[int] = None
) -> dict:
    """
    Carrega imagem padrão para um produto

    Args:
        path: Caminho da imagem padrão
        store_id: ID da loja/usuário
        product_id: ID do produto

    Returns:
        dict: Resultado da operação
    """
    # Validações iniciais
    if not product_id:
        return {'success': False, 'error': 'ID do produto é obrigatório'}

    if not path:
        return {'success': False, 'error': 'Caminho da imagem é obrigatório'}

    if not store_id:
        return {'success': False, 'error': 'ID da loja é obrigatório'}

    try:
        # Buscar produto
        product = await Produto.get_or_none(id=product_id, usuario_id=store_id)
        if not product:
            return {'success': False, 'error': 'Produto não encontrado'}

        # Verificar se já tem imagem
        if product.image_url:
            return {
                'success': True,
                'message': 'Produto já possui imagem',
                'existing_image': product.image_url,
            }

        # Validar extensão
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        file_ext = os.path.splitext(path)[1].lower()

        if file_ext not in allowed_extensions:
            return {
                'success': False,
                'error': f"Formato {file_ext} não suportado. Use: {', '.join(allowed_extensions)}",
            }

        # Verificar se o arquivo existe (opcional)
        if not os.path.exists(path):
            print(f'Aviso: Arquivo de imagem não encontrado em {path}')

        # Atualizar produto
        product.image_url = path
        await product.save()

        return {
            'success': True,
            'message': f'Imagem padrão adicionada com sucesso',
            'product_id': product_id,
            'image_path': path,
        }

    except Exception as e:
        error_msg = f'Erro ao carregar imagem: {str(e)}'
        print(error_msg)
        return {'success': False, 'error': error_msg}
