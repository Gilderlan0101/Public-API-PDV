from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from tortoise import fields, models


class CNPJCache(models.Model):
    id = fields.IntField(pk=True)
    cnpj = fields.CharField(max_length=14)
    data_json = fields.TextField()  # Armazena o JSON como string
    updated_at = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )

    # 🔹 Relacionamento com o usuário dono do cache
    usuario = fields.ForeignKeyField(
        'models.Usuario', related_name='cnpj_cache', null=True
    )

    # 🔹 Método para verificar se o cache ainda é válido
    def is_valid(self, ttl_minutes: int = 8) -> bool:
        return datetime.now(
            ZoneInfo('America/Sao_Paulo')
        ) - self.updated_at < timedelta(minutes=ttl_minutes)
