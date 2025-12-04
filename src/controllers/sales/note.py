# Arquivo: src/controllers/sales/note.py
from dataclasses import dataclass, field

from fastapi import HTTPException, status

from src.controllers.sales.receipt_build import build_receipt  # MANTIDO
from src.controllers.sales.sales import Checkout


@dataclass
class Note(Checkout):
    """Extensão de Checkout para gerar notas fiscais adicionais"""

    # ... (verifyFields mantido) ...

    async def createNote(self) -> dict:
        """Cria uma nota fiscal"""

        # Lógica específica para criação de nota
        if self.receipt_data:
            print(
                f'DEBUG NOTE: Gerando documento com {len(self.receipt_data)} itens.'
            )

            # 🟢 CORREÇÃO: Passar TODOS os argumentos requeridos e opcionais para build_receipt
            return await build_receipt(
                itens=self.receipt_data,
                # Argumentos Posicionais Requeridos
                usuario=self.usuario,  # Objeto Usuario (ou None, mas build_receipt valida)
                funcionario_nome=self.funcionario_nome
                or 'Não Informado',  # String
                sale_code=self.sale_code,  # String
                payment_method=self.payment_method,  # String
                # Argumentos Opcionais
                valor_recebido=self.valor_recebido,
                troco=self.troco,
                installments=self.installments,
                customer_id=self.customer_id,
                cpf=self.cpf,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail='Nenhum dado de venda disponível para criar nota.',
            )
