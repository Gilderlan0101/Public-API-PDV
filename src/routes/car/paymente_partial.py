# from fastapi import APIRouter, Depends, HTTPException, status
# from src.controllers.payments.partial import Person, PartialPayment
# from src.auth.deps import get_current_user, SystemUser
# from src.schemas.payments.payment_methods import RegisterUserForPartialMode, InputData


# partial = APIRouter(tags=['Pagamentos'])


# @partial.post('/cadastra-cliente')
# async def create_customers(data: RegisterUserForPartialMode, current_user: SystemUser = Depends(get_current_user)):
#     """
#     Endpoint para cadastrar um cliente para pagamentos parciais.
#     """

#     try:
#         person = Person(full_name=data.full_name, cpf=data.cpf, tel=data.tel, user_id=current_user.id)

#         created = await person.create_customer()

#         if created:
#             return {
#                 'status': 200,
#                 'menssagem': 'Cliente cadastrado com sucesso!',
#                 'name': data.full_name,
#                 'tel': data.tel,
#             }
#         else:
#             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erro ao cadastrar cliente")

#     except Exception as e:
#         # Log do erro no console
#         print(e)
#         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro interno: {str(e)}")


# # @router.post('/cadastra-cliente')
# # async def starts_sale_in_partial_mode(
# #     data: InputData,
# #     current_user: SystemUser = Depends(get_current_user)):
