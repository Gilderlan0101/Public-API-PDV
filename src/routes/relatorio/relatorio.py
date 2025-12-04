# from fastapi import APIRouter, Depends
# from src.controllers.report_controller import generate_report_pdv, load_logo
# from src.model.user import Usuario
# from src.auth.deps import get_current_user
# from datetime import date
# from typing import Optional


# router = APIRouter(tags=['relatorio'])

# # Carregar a logo uma vez na inicialização
# LOGO_BASE64 = load_logo(
#     image_path='/home/dev/projetos/API-PDV-ONLINE/back-end/static/images/logo_login.jpg',
#     base64_string=None,
# )

# @router.get("/pdv/{usuario_id}")
# async def baixar_pdv(
#     usuario_id: int,
#     start_date: Optional[date] = None,
#     end_date: Optional[date] = None,
#     current_user: Usuario = Depends(get_current_user),
# ):
#     """
#     Gera e baixa o relatório de vendas do PDV.

#     Args:
#         usuario_id: ID do usuário/empresa
#         start_date: Data inicial do relatório (opcional)
#         end_date: Data final do relatório (opcional)
#     """
#     return await generate_report_pdv(
#         usuario_id=usuario_id,
#         start_date=start_date,
#         end_date=end_date,
#         logo_base64=LOGO_BASE64
#     )
