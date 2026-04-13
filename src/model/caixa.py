# Model caixa
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from tortoise import fields, models


class Caixa(models.Model):
    """
    Modelo de Caixa vinculado a um usuário (empresa) e a um funcionário.
    Cada funcionário tem seu próprio caixa na empresa.
    """

    id = fields.IntField(pk=True)
    nome = fields.CharField(max_length=100)
    saldo_inicial = fields.FloatField(default=0.0)
    saldo_atual = fields.FloatField(default=0.0)
    valor_fechamento = fields.FloatField(null=True)
    valor_sistema = fields.FloatField(null=True)
    change = fields.FloatField(null=True)
    diferenca = fields.FloatField(null=True)
    aberto = fields.BooleanField(default=False)
    criado_em = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )

    # CAIXA_ID: Único por empresa, pode repetir entre empresas diferentes
    caixa_id = fields.IntField(null=False)

    atualizado_em = fields.DatetimeField(
        default=datetime.now(ZoneInfo('America/Sao_Paulo'))
    )
    valor_total = fields.FloatField(default=0.0)

    # 🔹 Relacionamentos
    usuario = fields.ForeignKeyField(
        'models.Usuario', related_name='caixas', on_delete=fields.CASCADE
    )
    funcionario = fields.ForeignKeyField(
        'models.Employees',
        related_name='caixas',
        null=True,
        on_delete=fields.SET_NULL,
    )

    class Meta:
        table = 'caixas'
        # ✅ Índice composto único: garante que caixa_id seja único POR EMPRESA
        unique_together = (('usuario_id', 'caixa_id'),)

    async def save(self, *args, **kwargs):
        """
        Sobrescreve save para gerar caixa_id único para a empresa antes de salvar
        """
        if not self.caixa_id and self.usuario_id:
            from src.utils.sales_code_generator import \
                generator_code_to_checkout

            self.caixa_id = await generator_code_to_checkout(self.usuario_id)

        await super().save(*args, **kwargs)
