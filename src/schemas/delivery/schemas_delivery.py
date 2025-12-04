from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DeliveryCreate(BaseModel):
    customer_name: str
    customer_id: Optional[int] = None
    address: Dict[str, str]
    items: List[Dict[str, Any]]
    delivery_type: str
    scheduled_time: Optional[datetime] = None
    cep: Optional[str] = None
    number_of_bags: Optional[int] = None
    delivery_man_id: Optional[int] = None


class DeliveryAssign(BaseModel):
    delivery_id: int
    driver_id: int


class DeliveryStatusUpdate(BaseModel):
    delivery_id: int
    new_status: str


class PaymentStatusUpdate(BaseModel):
    sales_id: int
    new_status: str
