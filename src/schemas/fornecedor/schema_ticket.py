from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class TicketCreateSchema(BaseModel):
    name: str
    description: Optional[str] = None


class TicketReadSchema(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    # criado_em: datetime
    # atualizado_em: datetime
