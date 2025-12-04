import requests

from src.services.consulting_docs import checking_documents_CNPJ


async def consulting_CNPJ(cnpj: str) -> dict:
    try:
        if not cnpj or len(cnpj) < 14:
            return {'status': 'Erro: CNPJ inválido ou ausente'}

        # Validando o número do CNPJ antes da consulta para evitar pesquisas desnecessárias no banco de dados e API
        doc = checking_documents_CNPJ(cnpj)

        if doc:

            url = f'https://receitaws.com.br/v1/cnpj/{cnpj}'
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('status') == 'ERROR':
                    return {
                        'status': f"Erro da API: {data.get('message', 'Sem detalhes')}"
                    }

                return {
                    'company_name': data.get('nome') or None,
                    'fantasy': data.get('fantasia') or None,
                    'cnpj': data.get('cnpj') or None,
                    'abertura': data.get('abertura') or None,
                    'atividade_principal': data.get('atividade_principal', []),
                    'atividades_secundarias': data.get(
                        'atividades_secundarias', []
                    ),
                    'information': {
                        'logradouro': data.get('logradouro') or None,
                        'numero': data.get('numero') or None,
                        'complemento': data.get('complemento') or None,
                        'cep': data.get('cep') or None,
                        'bairro': data.get('bairro') or None,
                        'municipio': data.get('municipio') or None,
                        'uf': data.get('uf') or None,
                        'email': data.get('email') or None,
                        'telefone': data.get('telefone') or None,
                        'situacao': data.get('situacao') or None,
                        'motivo_situacao': data.get('motivo_situacao') or None,
                    },
                    'qsa': data.get('qsa', []),  # lista de sócios
                    'simples': {
                        'optante': data.get('opcao_pelo_simples') or None,
                        'data_opcao': data.get('data_opcao_pelo_simples')
                        or None,
                    },
                }

            else:
                return {
                    'status': f'Erro {response.status_code}: Falha ao consultar a API CNPJ'
                }

    except requests.exceptions.RequestException as erro:
        return {
            'error': str(erro),
            'mensagem': 'Tente novamente mais tarde ou entre em contato com o suporte.',
        }
