from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from tortoise.transactions import in_transaction

from src.auth.deps import get_current_user
from src.model.tickets import Ticket
from src.model.user import Usuario
from src.schemas.fornecedor.schema_ticket import (TicketCreateSchema,
                                                  TicketReadSchema)

router = APIRouter(tags=['Tickets'])


@router.post('/criar', response_model=TicketReadSchema)
async def create_ticket(
    ticket: TicketCreateSchema,
    current_user: Usuario = Depends(get_current_user),
):
    # Verifica se o usuário já possui ticket com o mesmo nome
    existing_ticket = await Ticket.filter(
        name=ticket.name, usuario_id=current_user.id
    ).first()

    if existing_ticket:
        raise HTTPException(
            status_code=400,
            detail=f"Você já possui um ticket com o nome '{ticket.name}'",
        )

    async with in_transaction() as conn:
        # 🔹 CORREÇÃO: Defina as datas manualmente
        now = datetime.now(ZoneInfo('America/Sao_Paulo'))
        db_ticket = Ticket(
            **ticket.model_dump(),
            usuario_id=current_user.id,
            criado_em=now,
            atualizado_em=now,
        )
        await db_ticket.save(using_db=conn)
        await db_ticket.fetch_related('usuario')

    return db_ticket


# ========================
# 🔹 Listar tickets do usuário
# ========================
@router.get('/lista/', response_model=List[TicketReadSchema])
async def list_tickets(current_user: Usuario = Depends(get_current_user)):
    tickets = await Ticket.filter(usuario_id=current_user.id).all()
    return tickets


# ========================
# 🔹 Deletar ticket pelo ID
# ========================
@router.delete('/delete/{ticket_id}', response_model=dict)
async def delete_ticket(
    ticket_id: int, current_user: Usuario = Depends(get_current_user)
):
    ticket = await Ticket.filter(
        id=ticket_id, usuario_id=current_user.id
    ).first()
    if not ticket:
        raise HTTPException(status_code=404, detail='Ticket não encontrado')

    async with in_transaction() as conn:
        await ticket.delete(using_db=conn)

    return {'msg': 'Ticket removido com sucesso'}
