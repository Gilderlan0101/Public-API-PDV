import json
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Query, status

from src.model.user import CNPJCache, Usuario
from src.services.consulting_cnpj import consulting_CNPJ


class ConsultaRoute:
    def __init__(self):
        self.router = APIRouter(
            prefix='/consulta', tags=['Consulta CNPJ / Usuário']
        )
        self.startup_route()

    def startup_route(self):
        @self.router.get('/', status_code=status.HTTP_200_OK)
        async def consulta_dados(
            email: Optional[str] = Query(default=None),
            cnpj: Optional[str] = Query(default=None),
        ):
            if not email and not cnpj:
                raise HTTPException(
                    status_code=400,
                    detail='Você deve fornecer email ou cnpj para consulta.',
                )

            # 🔹 Busca usuário pelo email ou cnpj
            user = None
            if email:
                user = await Usuario.get_or_none(email=email)
            elif cnpj:
                user = await Usuario.get_or_none(cnpj=cnpj)

            if user:
                return {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'company_name': user.company_name,
                    'trade_name': user.trade_name,
                    'cpf': user.cpf,
                    'cnpj': user.cnpj,
                    'state_registration': user.state_registration,
                    'municipal_registration': user.municipal_registration,
                    'cnae_principal': user.cnae_principal,
                    'crt': user.crt,
                    'cep': user.cep,
                    'street': user.street,
                    'number': user.home_number,  # cuidado: no seu model tá "home_number"
                    'complement': user.complement,
                    'district': user.district,
                    'city': user.city,
                    'state': user.state,
                }

            # 🔹 Se não encontrou, tenta API do CNPJ
            if cnpj:
                cache = await CNPJCache.get_or_none(cnpj=cnpj)

                if cache and cache.is_valid():
                    data = json.loads(cache.data_json)
                else:
                    data = await consulting_CNPJ(cnpj)
                    if cache:
                        cache.data_json = json.dumps(data, ensure_ascii=False)
                        cache.updated_at = datetime.now(
                            ZoneInfo('America/Sao_Paulo')
                        )
                        await cache.save()
                    else:
                        await CNPJCache.create(
                            cnpj=cnpj,
                            data_json=json.dumps(data, ensure_ascii=False),
                            usuario=None,  # pode ser null se não vinculado a usuário
                        )

                return data

            raise HTTPException(
                status_code=404,
                detail='Nenhum dado encontrado para os parâmetros fornecidos.',
            )
