import json
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from src.auth.deps import SystemUser, get_current_user
from src.model.product import Produto
from src.model.user import Usuario
from src.schemas.schema_product import ProductUpdateSchema

router = APIRouter(prefix='/produtos', tags=['Produtos'])


@router.put('/atualizar', status_code=status.HTTP_200_OK)
async def update_product(
    code: Optional[str] = Query(None, description='Código do produto'),
    name: Optional[str] = Query(None, description='Nome do produto'),
    update_data: ProductUpdateSchema = Body(...),
    current_user: SystemUser = Depends(get_current_user),
):
    if not current_user.empresa_id:
        raise HTTPException(status_code=400, detail='Usuário inválido')

    # 🔹 Buscar produto pelo usuário
    product = await Produto.filter(
        usuario_id=current_user.empresa_id,
        **({'product_code': code} if code else {}),
        **({'name': name} if name else {}),
    ).first()

    if not product:
        raise HTTPException(status_code=404, detail='Produto não encontrado')

    data_to_update = update_data.model_dump(exclude_unset=True)
    updated_fields = {}

    for field, value in data_to_update.items():
        if isinstance(value, dict):
            value = json.dumps(value, ensure_ascii=False)

        if value in [None, '', 'string']:
            continue
        if isinstance(value, (int, float)) and value == 0:
            continue

        if field == 'date_expired' and isinstance(value, date):
            value = datetime.combine(value, datetime.min.time())
        elif field == 'image_url' and value:
            value = str(value)

        if getattr(product, field) != value:
            setattr(product, field, value)
            updated_fields[field] = value

    if not updated_fields:
        return {
            'message': 'Nenhum campo relevante para atualizar.',
            'product_id': product.id,
        }

    product.atualizado_em = datetime.now()
    await product.save()  # 🔹 Salva alterações no banco

    return {
        'message': 'Produto atualizado com sucesso!',
        'product_id': product.id,
        'dados_atualizados': updated_fields,
    }
