import re
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from tortoise import fields, models


class Pix(models.Model):
    """
    Modelo para armazenamento de dados PIX
    """

    id = fields.IntField(pk=True)
    full_name = fields.CharField(max_length=90, null=False)
    city = fields.CharField(max_length=90, null=False)
    key_pix = fields.CharField(max_length=140, unique=True, null=False)
    usuario_id = fields.IntField(null=False)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = 'pix'
        indexes = [('usuario_id', 'is_active'), ('key_pix',)]

    def __str__(self):
        return f'PIX {self.key_pix} - {self.full_name}'

    @property
    def created_at_brasil(self):
        """Retorna a data de criação no fuso horário do Brasil"""
        return self.created_at.astimezone(ZoneInfo('America/Sao_Paulo'))
