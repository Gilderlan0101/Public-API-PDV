from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.auth.deps import SystemUser, get_current_user
from src.model.product import Produto, ProdutoArquivado
from src.model.user import Usuario
from src.routes.products.helpers import to_dict

router = APIRouter()


@router.delete('/remove', status_code=status.HTTP_200_OK)
async def delete_product(
    code: str = Query(..., description='Código do produto'),
    description: str = Query(..., description='Motivo do arquivamento'),
    current_user: SystemUser = Depends(get_current_user),
):
    if not current_user.empresa_id:
        raise HTTPException(status_code=400, detail='Usuário inválido')

    # 🔹 Busca o produto único
    product = await Produto.filter(
        usuario_id=current_user.empresa_id, product_code=code
    ).first()
    if not product:
        raise HTTPException(
            status_code=404,
            detail='Produto não encontrado ou não pertence ao usuário',
        )

    # 🔹 Converte para dict e limpa campos desnecessários
    product_data = to_dict(product)
    product_data['description'] = description
    product_data.pop('id', None)
    product_data.pop('criado_em', None)
    product_data.pop('atualizado_em', None)

    # 🔹 Cria o ProdutoArquivado
    archived_product = ProdutoArquivado(**product_data)
    await archived_product.save()

    # 🔹 Remove o produto original
    await product.delete()

    return {
        'message': f"Produto '{product.name}' removido e arquivado com sucesso!",
        'usuario_id': current_user.empresa_id,
    }
