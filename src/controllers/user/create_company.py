from typing import Optional

from pydantic import EmailStr

from src.logs.infos import LOGGER
from src.model.user import CNPJCache, Usuario


class CreateCompany:

    # Dados Inicias
    def __init__(
        self,
        # Dados pessoais
        full_name: str,
        email: EmailStr,
        password: str,
        cpf: Optional[str] = None,
        phone: Optional[str] = None,
        # Dados da empresa
        cnpj: Optional[str] = None,
        company_name: Optional[str] = None,
        trade_name: Optional[str] = None,
        state_registration: Optional[str] = None,
        municipal_registration: Optional[str] = None,
        cnae_pricipal: Optional[str] = None,
        crt: Optional[int] = None,
        # Endereço
        cep: Optional[str] = None,
        street: Optional[str] = None,
        number: Optional[str] = None,
        complement: Optional[str] = None,
        district: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
    ):

        # Dados pessoais
        self.full_name = full_name
        self.email = email
        self.password = password
        self.cpf = cpf
        self.phone = phone
        # Dados da empresa
        self.cnpj = cnpj
        self.company_name = company_name
        self.trade_name = trade_name
        self.state_registration = state_registration
        self.municipal_registration = municipal_registration
        self.cnae_pricipal = cnae_pricipal
        self.crt = crt
        # Endereço
        self.cep = cep
        self.street = street
        self.number = number
        self.complement = complement
        self.district = district
        self.city = city
        self.state = state

    async def new_company(self) -> list[dict[str, Any]]:
        """Metodo para cadastra uma nova empresa"""

        try:
            # Antes de cadastra crie uma hash da senha
            from src.auth.auth_jwt import hashed_password

            hashed_password = get_hashed_password(self.password)

            # Cadastra uma empresa
            data_company = Usuario(
                username=self.full_name,
                email=self.email,
                password=hashed_password,
                company_name=self.company_name,
                trade_name=self.trade_name,
                membros=0,  # Quantidade de filias Default 0
                cpf=self.cpf,
                cnpj=self.cnpj,
                state_registration=self.state_registration,
                municipal_registration=self.municipal_registration,
                cnae_pricipal=self.cnae_pricipal,
                crt=self.crt,
                cep=self.cep,
                street=self.street,
                number=self.number,
                complement=self.complement,
                district=self.district,
                city=self.city,
                state=self.state,
            )

        except Exception as e:
            LOGGER.error(f'Erro ao cadastra uma empresa: {e}')
            return None

        try:

            # Criando tickts padrão
            async with in_transaction as conn:
                await data_company.save(using_db=conn)

                if self.cnpj:
                    from ..services.consulting_cnpj import consulting_CNPJ

                    searching_for_data = await consulting_CNPJ(str(self.cnpj))

                    full_data = CNPJCache(
                        cnpj=self.cnpj,
                        data_json=json.dumps(
                            searching_for_data, ensure_ascii=False
                        ),
                        company_id=data_company.id,
                    )
                    await full_data.save(using_db=conn)

            # Tickets gerados automaticamente ao cria uma empresa
            from src.model.tickets import criar_tickets_padrao

            await criar_tickets_padrao(data_company)

            # Retorno seguro (sem senha)
            return {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'empresa': new_user.company_name,
                'criado_em': new_user.criado_em.strftime('%d/%m/%Y %H:%M:%S'),
            }

        except Exception as e:
            LOGGER.error(
                'Error: Erro ao tenta criar tickets padrão para empresa.'
                'Talvez voce tenha que cria manualmente em /tickets/'
                'Ou chame a função criar_tickets_padrao(table: Object).'
            )
            return None
