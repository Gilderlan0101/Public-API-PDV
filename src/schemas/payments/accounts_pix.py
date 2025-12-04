from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

# --- Esquema Pydantic (Exemplo) ---
# Adicione este modelo em um arquivo de schemas ou no topo da sua rota/serviço


class PixAccountResponse(BaseModel):
    id: int
    full_name: str
    city: str
    key_pix: str
    usuario_id: int
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # Isso era orm_mode = True no Pydantic v1


class PixAccountsList(BaseModel):
    count: int
    accounts: List[PixAccountResponse]
