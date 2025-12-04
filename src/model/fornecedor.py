from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from tortoise import fields, models

from src.model.product import Produto


# ========================
# 🔹 Enums
# ========================
class SupplierType(str, Enum):
    PESSOA_JURIDICA = 'PJ'
    PESSOA_FISICA = 'PF'


class TaxRegime(str, Enum):
    SIMPLES_NACIONAL = 'Simples Nacional'
    LUCRO_PRESUMIDO = 'Lucro Presumido'
    LUCRO_REAL = 'Lucro Real'
    MEI = 'MEI'
    OUTRO = 'Outro'


class IEStatus(str, Enum):
    CONTRIBUINTE = 'Contribuinte'
    ISENTO = 'Isento'
    NAO_CONTRIBUINTE = 'Não Contribuinte'


class PaymentTerm(str, Enum):
    AVISTA = 'À vista'
    DIAS_7 = '7 dias'
    DIAS_14 = '14 dias'
    DIAS_21 = '21 dias'
    DIAS_28 = '28 dias'
    DIAS_30 = '30 dias'
    DIAS_45 = '45 dias'
    DIAS_60 = '60 dias'
    PERSONALIZADO = 'Personalizado'


class SupplierStatus(str, Enum):
    ATIVO = 'Ativo'
    INATIVO = 'Inativo'
    BLOQUEADO = 'Bloqueado'
    PENDENTE = 'Pendente'


# ========================
# 🔹 Fornecedor - MODELO CORRIGIDO
# ========================
class Fornecedor(models.Model):
    id = fields.IntField(pk=True)
    tipo = fields.CharEnumField(
        SupplierType, default=SupplierType.PESSOA_JURIDICA
    )
    razao_social = fields.CharField(max_length=200)
    nome_fantasia = fields.CharField(max_length=200, null=True)

    # REMOVER unique=True ou usar index=True apenas
    cnpj = fields.CharField(
        max_length=14, null=True, index=True
    )  # Removido unique=True
    cpf = fields.CharField(
        max_length=11, null=True, index=True
    )  # Removido unique=True

    ie_status = fields.CharEnumField(IEStatus, default=IEStatus.CONTRIBUINTE)
    inscricao_estadual = fields.CharField(max_length=20, null=True)
    inscricao_municipal = fields.CharField(max_length=20, null=True)
    regime_tributario = fields.CharEnumField(
        TaxRegime, default=TaxRegime.SIMPLES_NACIONAL
    )
    email = fields.CharField(max_length=200, null=True)

    # Campos JSON com valores padrão
    telefones = fields.JSONField(default=list)
    site = fields.CharField(max_length=200, null=True)
    contato_principal = fields.JSONField(null=True)
    contatos_secundarios = fields.JSONField(default=list)
    endereco = fields.JSONField()  # Tornar obrigatório se sempre existir
    prazo_pagamento = fields.CharEnumField(
        PaymentTerm, default=PaymentTerm.DIAS_30
    )
    prazo_personalizado_dias = fields.IntField(null=True)
    limite_credito = fields.FloatField(default=0)
    desconto_padrao_percent = fields.FloatField(default=0)
    contas_bancarias = fields.JSONField(default=list)
    categorias_fornecimento = fields.JSONField(default=list)
    observacoes = fields.TextField(null=True)
    status = fields.CharEnumField(SupplierStatus, default=SupplierStatus.ATIVO)
    ativo_desde = fields.DateField(null=True)
    criado_por = fields.CharField(max_length=100, null=True)
    atualizado_por = fields.CharField(max_length=100, null=True)
    criado_em = fields.DatetimeField(auto_now_add=True)
    atualizado_em = fields.DatetimeField(auto_now=True)

    # 🔹 Relacionamentos
    usuario = fields.ForeignKeyField(
        'models.Usuario', related_name='fornecedores', on_delete=fields.CASCADE
    )
    produtos: fields.ReverseRelation['Produto']

    class Meta:
        table = 'fornecedores'

    def __str__(self):
        return f'{self.razao_social} ({self.tipo})'
