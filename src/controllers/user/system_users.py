import json
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from tortoise.functions import Count

from src.model.user import Usuario


class LoginInSystem:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def _adminSystem(self):
        __data_login = {
            'username': 'nathec@gmail.com',
            'password': '_py3go5BZ}61FhC99kwi',
        }

        if self.username == __data_login.get(
            'username'
        ) and self.password == __data_login.get('password'):
            return True
        else:
            return False


@dataclass
class SystemUser:
    # Iniciando variáveis vazias
    data: list = field(
        default_factory=list
    )  # Lista de objetos com informações
    users_active: int = 0  # Quantidade de usuários ativos
    pending: int = 0  # Quantidade de usuários pendentes

    # Verificando se o usuário tem permissão para acessar o sistema
    async def VerifyLogin(self, username, password):
        login = LoginInSystem(username, password)
        result = login._adminSystem()

        if result:
            await self.FeedingSystem()
        else:
            return False

    async def FeedingSystem(self):
        users = await Usuario.all().values(
            'company_name', 'cnpj', 'cpf', 'email', 'is_active'
        )

        for customer in users:
            if customer['is_active']:
                self.users_active += 1
                self.data.append(
                    {
                        'company_name': customer['company_name'],
                        'cnpj': customer['cnpj'],
                        'email': customer['email'],
                        'status': customer['is_active'],
                        'amount': self.users_active,
                    }
                )

    async def UpdateIs_active(self, customer_id: int):
        """Atualiza dados de um cliente"""
        try:
            # Buscando o cliente pelo ID
            customer = await Usuario.filter(id=customer_id).first()
            if customer:
                if customer.is_active:
                    # Desativando a conta
                    await Usuario.filter(id=customer_id).update(
                        is_active=False
                    )
                    return {
                        'aviso': f'Cliente {customer_id} desativado com sucesso!'
                    }
                else:
                    return False
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f'Cliente {customer_id} não encontrado.',
                )

        except Exception as e:
            print('Erro ao atualizar cliente:', e)
            raise HTTPException(
                status_code=500, detail='Entre em contato com o desenvolvedor.'
            )

    async def UpdateIs_pending(self, customer_id: int):
        """Atualiza dados de um cliente"""
        try:
            # Buscando o cliente pelo ID
            customer = await Usuario.filter(id=customer_id).first()
            if customer:
                if customer.pending:
                    # Desativando a conta
                    await Usuario.filter(id=customer_id).update(pending=False)
                    return {
                        'aviso': f'Cliente {customer.username} agora esta ativo.'
                    }
                else:
                    return False
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f'Cliente {customer.username} não encontrado.',
                )

        except Exception as e:
            print('Erro ao atualizar cliente:', e)
            raise HTTPException(
                status_code=500, detail='Entre em contato com o desenvolvedor.'
            )

    async def ViewInfoCustomes(self):
        """Visualiza todos os dados do cliente"""
        try:
            customer = await Usuario.all()

            if customer:
                for user in customer:
                    self.data.append(
                        {
                            'user_data': {
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
                                'home_number': user.home_number,
                                'complement': user.complement,
                                'district': user.district,
                                'city': user.city,
                                'state': user.state,
                                'is_active': user.is_active,
                                'criado_em': user.criado_em,
                                'pending': user.pending,
                            }
                        }
                    )

                print(self.data)
            else:
                raise HTTPException(
                    status_code=404, detail='Cliente não encontrado'
                )

        except Exception as e:
            print('Erro ao visualizar cliente:', e)
            raise HTTPException(status_code=500, detail=str(e))

    async def UsersPending(self):
        """Retorna a quantidade de usuários pendentes"""
        try:
            # Exemplo: se você tiver um campo `pending=True/False`
            users_pending = await Usuario.filter(pending=False).all()

            if users_pending:
                self.data.append({'pending': len(users_pending)})

            return len(users_pending)

        except Exception as e:
            print('Erro em UsersPending:', e)

    async def NewUsersThisMonth(self):
        """Retorna a quantidade de usuários cadastrados no mês atual"""
        try:
            now = datetime.now(ZoneInfo('America/Sao_Paulo'))
            start_of_month = now.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )

            # Busca todos os clientes criados a partir do 1º dia do mês
            total = await Usuario.filter(criado_em__gte=start_of_month).count()
            self.data.append({'total_customer': total})

        except Exception as e:
            print('Erro ao contar novos clientes:', e)
            return {'novos_clientes_mes': 0}

    @property
    def view(self):
        # Dicionário para agrupar por CPF (chave única)
        dividas_por_cliente = {}

        depts_list = self.data  # Lista de todas as dívidas

        print('TODAS AS DÍVIDAS RECEBIDAS:', depts_list)
        print()

        for divida in depts_list:
            cpf = divida['cpf']

            # Se é a primeira vez que vemos este CPF, adiciona ao dicionário
            if cpf not in dividas_por_cliente:
                dividas_por_cliente[cpf] = divida
                print(f'✅ Nova dívida adicionada para CPF: {cpf}')
            else:
                print(f'🔄 CPF {cpf} já existe, atualizando dados...')

                # Aqui você pode escolher como consolidar os dados:
                # Opção 1: Manter a dívida mais recente (pela data)
                data_existente = dividas_por_cliente[cpf]['date']
                data_nova = divida['date']

                if data_nova > data_existente:
                    dividas_por_cliente[cpf] = divida
                    print(f'   ↳ Atualizado para dívida mais recente')

                # Opção 2: Somar os valores (se for o caso)
                # valor_existente = float(dividas_por_cliente[cpf]['value'])
                # valor_novo = float(divida['value'])
                # dividas_por_cliente[cpf]['value'] = str(valor_existente + valor_novo)
                # print(f'   ↳ Valor somado: {valor_existente} + {valor_novo}')

        print()
        print(f'📊 Total de clientes únicos: {len(dividas_por_cliente)}')

        # Retorna apenas os valores (sem os CPFs como chaves)
        return list(dividas_por_cliente.values())
