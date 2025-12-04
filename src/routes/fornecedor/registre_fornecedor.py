import json
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from tortoise.functions import Count
from tortoise.transactions import in_transaction

from src.auth.deps import get_current_user
from src.model.fornecedor import Fornecedor, SupplierStatus
from src.model.user import Usuario
from src.schemas.fornecedor.schemas_fornecedor import (
    SupplierBase,
    SupplierCreate,
    SupplierListResponse,
    SupplierSummary,
)
from src.schemas.fornecedor.update_spplierBase import SupplierUpdate

router = APIRouter()


# ===============================
# Criar fornecedor - CORRIGIDO
# ===============================
@router.post('/cadastra/', status_code=status.HTTP_201_CREATED)
async def create_fornecedor(
    fornecedor: SupplierCreate,
    current_user: Usuario = Depends(get_current_user),
):
    if not current_user.id:
        raise HTTPException(status_code=400, detail='Usuário inválido')

    async with in_transaction() as conn:
        try:
            # Validar duplicidade de CNPJ/CPF apenas se fornecidos
            if fornecedor.cnpj:
                exists = (
                    await Fornecedor.filter(cnpj=fornecedor.cnpj)
                    .using_db(conn)
                    .first()
                )
                if exists:
                    raise HTTPException(
                        status_code=400, detail='CNPJ já cadastrado'
                    )

            if fornecedor.cpf:
                exists = (
                    await Fornecedor.filter(cpf=fornecedor.cpf)
                    .using_db(conn)
                    .first()
                )
                if exists:
                    raise HTTPException(
                        status_code=400, detail='CPF já cadastrado'
                    )

            # Preparar dados para o Tortoise
            data = fornecedor.model_dump()

            # DEBUG: Log dos dados recebidos
            print('=== DADOS RECEBIDOS DO FRONTEND ===')
            print(json.dumps(data, indent=2, default=str))

            # Converter campos complexos para JSON/dict com valores padrão
            data['telefones'] = data.get('telefones', [])
            data['contatos_secundarios'] = data.get('contatos_secundarios', [])
            data['contas_bancarias'] = data.get('contas_bancarias', [])
            data['categorias_fornecimento'] = data.get(
                'categorias_fornecimento', []
            )

            # Garantir que endereço existe
            if not data.get('endereco'):
                raise HTTPException(
                    status_code=400, detail='Endereço é obrigatório'
                )

            # Garantir que contato_principal existe
            if not data.get('contato_principal'):
                raise HTTPException(
                    status_code=400, detail='Contato principal é obrigatório'
                )

            # Tratar campos opcionais
            data['nome_fantasia'] = data.get('nome_fantasia') or None
            data['site'] = str(data['site']) if data.get('site') else None
            data['inscricao_municipal'] = (
                data.get('inscricao_municipal') or None
            )
            data['observacoes'] = data.get('observacoes') or None
            data['ativo_desde'] = data.get('ativo_desde') or None

            # Campos de auditoria
            data['criado_por'] = str(current_user.id)
            data['atualizado_por'] = str(current_user.id)
            data['usuario_id'] = current_user.id

            # Remover campos que não existem no modelo Tortoise
            campos_modelo = [
                field for field in Fornecedor._meta.fields_map.keys()
            ]
            data_final = {k: v for k, v in data.items() if k in campos_modelo}

            # DEBUG: Log dos dados finais
            print('=== DADOS FINAIS PARA CRIAÇÃO ===')
            print(json.dumps(data_final, indent=2, default=str))
            print(f'Campos do modelo: {campos_modelo}')

            # Criar fornecedor
            register_forn = await Fornecedor.create(
                **data_final, using_db=conn
            )

            return {
                'message': 'Fornecedor cadastrado com sucesso!',
                'fornecedor_id': register_forn.id,
                'usuario_id': current_user.id,
            }

        except HTTPException:
            raise
        except Exception as e:
            print(f'Erro detalhado ao criar fornecedor: {str(e)}')
            print(f'Tipo do erro: {type(e)}')
            raise HTTPException(
                status_code=400, detail=f'Erro ao criar fornecedor: {str(e)}'
            )


# ===============================
# Listar fornecedores - CORRIGIDO
# ===============================
@router.get('/listar', response_model=SupplierListResponse)
async def list_fornecedores(
    current_user: Usuario = Depends(get_current_user),
    page: int = 1,
    size: int = 20,
):
    try:
        offset = (page - 1) * size
        fornecedores = (
            await Fornecedor.filter(usuario_id=current_user.id)
            .offset(offset)
            .limit(size)
        )
        total_count = await Fornecedor.filter(
            usuario_id=current_user.id
        ).count()

        data = []
        for f in fornecedores:
            # Parse dos campos JSON
            endereco = f.endereco or {}

            data.append(
                SupplierSummary(
                    id=f.id,
                    razao_social=f.razao_social,
                    nome_fantasia=f.nome_fantasia,
                    cnpj=f.cnpj,
                    cpf=f.cpf,
                    email=f.email,
                    status=f.status,
                    cidade=endereco.get('cidade', ''),
                    uf=endereco.get('uf', ''),
                )
            )

        return SupplierListResponse(
            success=True,
            total=total_count,
            page=page,
            pages=(total_count // size) + (1 if total_count % size > 0 else 0),
            data=data,
        )
    except Exception as e:
        print(f'Erro ao listar fornecedores: {str(e)}')
        raise HTTPException(
            status_code=500, detail='Erro interno ao listar fornecedores'
        )


# ===============================
# Deletar fornecedor
# ===============================
@router.delete('/apagar/{fornecedor_id}', status_code=status.HTTP_200_OK)
async def delete_fornecedor(
    fornecedor_id: int, current_user: Usuario = Depends(get_current_user)
):
    async with in_transaction() as conn:
        fornecedor = (
            await Fornecedor.filter(
                id=fornecedor_id, usuario_id=current_user.id
            )
            .using_db(conn)
            .first()
        )

        if not fornecedor:
            raise HTTPException(
                status_code=404, detail='Fornecedor não encontrado'
            )

        await fornecedor.delete(using_db=conn)
        return {'message': 'Fornecedor deletado com sucesso!'}


# ===============================
# Atualizar fornecedor - CORRIGIDO
# ===============================
@router.put('/atualiza/{fornecedor_id}', status_code=status.HTTP_200_OK)
async def update_fornecedor(
    fornecedor_id: int,
    form: SupplierUpdate,
    current_user: Usuario = Depends(get_current_user),
):
    async with in_transaction() as conn:
        # Busca o fornecedor
        fornecedor = (
            await Fornecedor.filter(
                id=fornecedor_id, usuario_id=current_user.id
            )
            .using_db(conn)
            .first()
        )

        if not fornecedor:
            raise HTTPException(
                status_code=404, detail='Fornecedor não encontrado'
            )

        # Evita duplicidade de CNPJ/CPF se vierem no update
        update_data = form.model_dump(exclude_unset=True)

        if 'cnpj' in update_data and update_data['cnpj'] != fornecedor.cnpj:
            exists = (
                await Fornecedor.filter(cnpj=update_data['cnpj'])
                .exclude(id=fornecedor_id)
                .using_db(conn)
                .first()
            )
            if exists:
                raise HTTPException(
                    status_code=400, detail='CNPJ já cadastrado'
                )

        if 'cpf' in update_data and update_data['cpf'] != fornecedor.cpf:
            exists = (
                await Fornecedor.filter(cpf=update_data['cpf'])
                .exclude(id=fornecedor_id)
                .using_db(conn)
                .first()
            )
            if exists:
                raise HTTPException(
                    status_code=400, detail='CPF já cadastrado'
                )

        # Atualizar apenas campos existentes no modelo
        campos_modelo = [field for field in Fornecedor._meta.fields_map.keys()]
        for key, value in update_data.items():
            if key in campos_modelo:
                # Tratar campos especiais
                if key == 'site' and value is not None:
                    value = str(value)
                setattr(fornecedor, key, value)

        # Atualiza dados de auditoria
        fornecedor.atualizado_por = str(current_user.id)
        await fornecedor.save(using_db=conn)

        return {
            'message': 'Fornecedor atualizado com sucesso!',
            'fornecedor_id': fornecedor.id,
        }
