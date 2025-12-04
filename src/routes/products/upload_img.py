import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from tortoise.transactions import in_transaction

from src.auth.deps import SystemUser, get_current_user
from src.model.product import Produto

router = APIRouter()

# Diretório onde as imagens serão salvas
IMAGES_DIR = Path('static/images')
IMAGES_DIR.mkdir(parents=True, exist_ok=True)


# ===============================
# Upload de imagem do produto
# ===============================
@router.post('/produto/{product_id}/upload-imagem')
async def upload_image(
    product_id: int,
    file: UploadFile = File(...),
    current_user: SystemUser = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail='Usuário não autenticado')

    # Verifica extensão permitida
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, detail='Formato de arquivo não suportado'
        )

    # Busca o produto verificando o usuário
    produto = await Produto.filter(
        id=product_id, usuario_id=current_user.empresa_id
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail='Produto não encontrado')

    # Gera nome único para o arquivo
    unique_filename = (
        f'produto_{product_id}_{current_user.empresa_id}{file_ext}'
    )
    file_path = IMAGES_DIR / unique_filename

    try:
        # Salva o arquivo de forma assíncrona
        with open(file_path, 'wb') as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Remove imagem anterior se existir e for diferente
        if produto.image_url:
            old_filename = os.path.basename(produto.image_url)
            if old_filename != unique_filename:
                old_path = IMAGES_DIR / old_filename
                if old_path.exists():
                    old_path.unlink()

        # Atualiza a URL da imagem no banco (caminho relativo)
        produto.image_url = unique_filename  # Salva apenas o nome do arquivo
        await produto.save()

        return {
            'message': 'Imagem enviada com sucesso',
            'image_url': f'/produtos/produto/{product_id}/imagem',
            'filename': unique_filename,
        }

    except Exception as e:
        # Limpa o arquivo em caso de erro
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=500, detail=f'Erro ao salvar imagem: {str(e)}'
        )


# ===============================
# Exibir imagem do produto
# ===============================
@router.get('/produto/{product_id}/imagem')
async def get_image(
    product_id: int, current_user: SystemUser = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail='Usuário não autenticado')

    produto = await Produto.filter(
        usuario_id=current_user.empresa_id, id=product_id
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail='Produto não encontrado')

    if not produto.image_url:
        # Retorna imagem padrão se não tiver imagem
        default_path = Path('static/images/NAHTEC-SIMBOLO.png')
        if default_path.exists():
            return FileResponse(
                default_path,
                media_type='image/png',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': 'public, max-age=3600',
                },
            )
        raise HTTPException(status_code=404, detail='Imagem não encontrada')

    # CORREÇÃO: Busca a imagem no diretório de imagens
    filename = produto.image_url

    # Se for um caminho completo, extrai apenas o nome do arquivo
    if '/' in filename:
        filename = os.path.basename(filename)

    file_path = IMAGES_DIR / filename

    if not file_path.exists():
        # Fallback para imagem padrão
        default_path = Path('static/images/NAHTEC-SIMBOLO.png')
        if default_path.exists():
            return FileResponse(
                default_path,
                media_type='image/png',
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Cache-Control': 'public, max-age=3600',
                },
            )
        raise HTTPException(
            status_code=404, detail='Arquivo de imagem não encontrado'
        )

    # Content-Type
    extension_to_type = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }
    content_type = extension_to_type.get(
        file_path.suffix.lower(), 'image/jpeg'
    )

    return FileResponse(
        file_path,
        media_type=content_type,
        headers={
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'public, max-age=3600',
        },
    )


# ===============================
# Remover imagem do produto
# ===============================
@router.delete('/produto/{product_id}/imagem')
async def delete_image(
    product_id: int, current_user: SystemUser = Depends(get_current_user)
):
    if not current_user:
        raise HTTPException(status_code=401, detail='Usuário não autenticado')

    produto = await Produto.filter(
        id=product_id, usuario_id=current_user.empresa_id
    ).first()
    if not produto:
        raise HTTPException(status_code=404, detail='Produto não encontrado')

    if not produto.image_url:
        raise HTTPException(
            status_code=404, detail='Produto não possui imagem'
        )

    try:
        # Remove o arquivo físico
        filename = os.path.basename(produto.image_url)
        file_path = IMAGES_DIR / filename
        if file_path.exists():
            file_path.unlink()

        # Remove a referência no banco
        produto.image_url = None
        await produto.save()

        return {'message': 'Imagem removida com sucesso'}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f'Erro ao remover imagem: {str(e)}'
        )


# ===============================
# Rota OPTIONS para CORS preflight
# ===============================
@router.options('/produto/{product_id}/imagem')
async def options_image(product_id: int):
    return {
        'Allow': 'GET, OPTIONS',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    }
