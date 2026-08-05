from fastapi import APIRouter, Depends, HTTPException
from src.crud import AccountCRUD, get_account_crud
from src.schemes import Account, DepositRequest, WithdrawRequest, WithdrawResponse
from src.services.verify import VerifyBearer
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])
security = VerifyBearer()


@router.get("/account", response_model=Account, status_code=HTTP_200_OK)
async def get_account(
    payload: dict = Depends(security),
    account_crud: AccountCRUD = Depends(get_account_crud),
):
    username = payload.get("sub", "")
    account = await account_crud.get_account(username)
    if account is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Account not found")
    return Account(username=account.username, balance=account.balance)


@router.post("/deposit", response_model=Account, status_code=HTTP_200_OK)
async def deposit(
    request: DepositRequest,
    payload: dict = Depends(security),
    account_crud: AccountCRUD = Depends(get_account_crud),
):
    username = payload.get("sub", "")
    account = await account_crud.get_account(username)
    if account is None:
        raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Account not found")

    account = await account_crud.deposit(username, request.amount)
    return Account(username=account.username, balance=account.balance)


@router.post("/withdraw", response_model=WithdrawResponse, status_code=HTTP_200_OK)
async def withdraw(
    request: WithdrawRequest,
    payload: dict = Depends(security),
    account_crud: AccountCRUD = Depends(get_account_crud),
):
    username = payload.get("sub", "")
    account = await account_crud.withdraw(username, request.amount)
    if account is None:
        existing = await account_crud.get_account(username)
        if existing is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Account not found")
        return WithdrawResponse(success=False, balance=existing.balance)

    return WithdrawResponse(success=True, balance=account.balance)
