from typing import Any, Optional

from fastapi import Form
from fastapi.security import OAuth2PasswordRequestForm


class CustomOAuth2PasswordRequestForm(OAuth2PasswordRequestForm):
    def __init__(
        self,
        username: str = Form(...),
        password: str = Form(...),
        valor_inicial: float = Form(...),
        scope: str = Form(''),
        grant_type: str = Form(None),
        client_id: str = Form(None),
        client_secret: str = Form(None),
    ):
        super().__init__(
            username=username,
            password=password,
            scope=scope,
            grant_type=grant_type,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.valor_inicial = valor_inicial
