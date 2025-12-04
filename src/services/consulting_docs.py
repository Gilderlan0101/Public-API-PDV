from validate_docbr import CNPJ, CPF


def checking_documents_CPF(doc: str) -> bool:

    cpf = CPF()
    number_cpf = doc

    if not doc:
        return False

    elif cpf.validate(number_cpf):
        return True

    else:
        return False


def checking_documents_CNPJ(doc: str) -> bool:

    cnpj = CNPJ()
    number_cnpj = doc

    if not doc:
        return False

    elif cnpj.validate(number_cnpj):
        return True
    else:
        return False
