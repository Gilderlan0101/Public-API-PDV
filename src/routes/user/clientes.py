# src/routes/system_user.py
from fastapi import APIRouter, HTTPException

from src.controllers.user.system_users import LoginInSystem, SystemUser

router = APIRouter(prefix='/system-user', tags=['System User'])


@router.post('/login')
async def verify_login(username: str, password: str):
    system = SystemUser()
    result = LoginInSystem(username, password)
    if not result:
        raise HTTPException(status_code=401, detail='Acesso negado')
    return {'message': 'Login realizado com sucesso'}


@router.get('/feeding')
async def feeding_system():
    system = SystemUser()
    await system.FeedingSystem()
    return system.view()


@router.put('/update-active/{customer_id}')
async def update_is_active(customer_id: int):
    system = SystemUser()
    return await system.UpdateIs_active(customer_id)


@router.put('/update-pending/{customer_id}')
async def update_is_pending(customer_id: int):
    system = SystemUser()
    return await system.UpdateIs_pending(customer_id)


@router.get('/customer/')
async def view_info_customer():
    system = SystemUser()
    await system.ViewInfoCustomes()
    return system.view()


@router.get('/pending')
async def users_pending():
    system = SystemUser()
    await system.UsersPending()
    return system.view()


@router.get('/new-this-month')
async def new_users_this_month():
    system = SystemUser()
    await system.NewUsersThisMonth()
    return system.view()
