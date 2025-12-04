import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status

from src.auth.deps import SystemUser, get_current_user
from src.model.product import Produto
from src.model.user import Usuario
from src.schemas.schema_product import ProductRegisterSchema
from src.utils.load_images import load_imgs
from src.utils.sales_code_generator import (
    gerar_codigo_venda,
    lot_bar_code_size,
)

load_dotenv()


PATH_IMG = os.getenv('PATH_IMG_DEFAULT_PRODUCTS')

router = APIRouter(prefix='/produtos', tags=['Produtos'])


@router.post('/criar', status_code=status.HTTP_201_CREATED)
async def create_product(
    prod: ProductRegisterSchema,
    current_user: SystemUser = Depends(get_current_user),
):
    if not current_user or not current_user.id:
        raise HTTPException(status_code=400, detail='Usuário inválido')

    try:
        date_expired = (
            datetime.combine(prod.date_expired, datetime.min.time())
            if prod.date_expired
            else None
        )
        image_url = str(prod.image_url) if prod.image_url else None
        product_code = (
            prod.product_code if prod.product_code else gerar_codigo_venda()
        )
        barcode = (
            prod.lot_bar_code if prod.lot_bar_code else lot_bar_code_size()
        )

        # Criar produto
        register_prod = await Produto.create(
            product_code=product_code,
            name=prod.name,
            stock=prod.stock,
            stoke_min=prod.stoke_min,
            stoke_max=prod.stoke_max,
            date_expired=date_expired,
            fabricator=prod.fabricator,
            cost_price=prod.cost_price,
            price_uni=prod.price_uni,
            sale_price=prod.sale_price,
            supplier=prod.supplier,
            lot_bar_code=barcode,
            image_url=image_url,
            usuario_id=current_user.empresa_id,
            product_type=prod.product_type,
            active=prod.active,
            group=prod.group,
            sub_group=prod.sub_group,
            sector=prod.sector,
            ticket=prod.ticket,
            unit=prod.unit,
            controllstoke=prod.controllstoke,
            sales_config=(
                prod.sales_config.model_dump_json()
                if prod.sales_config
                else None
            ),
        )

        # CORREÇÃO: Verificar se o produto precisa de imagem padrão
        if not image_url:
            print(f'Produto sem imagem: ID {register_prod.id}')

            # Adiciona uma imagem padrão
            try:
                result = await load_imgs(
                    path=PATH_IMG,
                    store_id=current_user.empresa_id,
                    product_id=register_prod.id,
                )
                print(f'Imagem padrão adicionada: {result}')
            except Exception as img_error:
                print(f'Erro ao adicionar imagem padrão: {img_error}')
                # Não levantar exceção aqui para não interromper o cadastro

        return {
            'message': 'Produto cadastrado com sucesso!',
            'product_id': register_prod.id,
            'usuario_id': current_user.id,
        }

    except Exception as e:
        # CORREÇÃO: Mostrar erro real em vez de apenas "0"
        print(f'Erro detalhado ao criar produto: {e}')
        raise HTTPException(
            status_code=400, detail=f'Erro ao criar produto: {str(e)}'
        )
