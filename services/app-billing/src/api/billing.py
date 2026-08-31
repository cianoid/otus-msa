from fastapi import APIRouter, Depends, Header, HTTPException
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND

from src.core.tracing import start_span
from src.crud import AccountCRUD, get_account_crud
from src.schemes import Account, DepositRequest, WithdrawRequest, WithdrawResponse
from src.services.verify import VerifyBearer

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])
security = VerifyBearer()


@router.get("/account", response_model=Account, status_code=HTTP_200_OK)
async def get_account(
    payload: dict = Depends(security),
    account_crud: AccountCRUD = Depends(get_account_crud),
):
    username = payload.get("sub", "")
    with start_span("billing.get_account", attributes={"billing.username": username}):
        account = await account_crud.get_account(username)
        if account is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Account not found")
        return Account(username=account.username, balance=account.balance)


@router.post("/deposit", response_model=Account, status_code=HTTP_200_OK)
async def deposit(
    request: DepositRequest,
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    payload: dict = Depends(security),
    account_crud: AccountCRUD = Depends(get_account_crud),
):
    username = payload.get("sub", "")
    with start_span(
        "billing.deposit",
        attributes={
            "billing.username": username,
            "billing.amount": str(request.amount),
            "idempotency_key": x_idempotency_key,
        },
    ):
        account = await account_crud.get_account(username)
        if account is None:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Account not found")

        result = await account_crud.idempotent_deposit(x_idempotency_key, username, request.amount)
        if result.get("error") == "account_not_found":
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Account not found")
        return Account(username=result["username"], balance=result["balance"])


@router.post("/withdraw", response_model=WithdrawResponse, status_code=HTTP_200_OK)
async def withdraw(
    request: WithdrawRequest,
    x_idempotency_key: str | None = Header(None, alias="X-Idempotency-Key"),
    payload: dict = Depends(security),
    account_crud: AccountCRUD = Depends(get_account_crud),
):
    username = payload.get("sub", "")
    with start_span(
        "billing.withdraw",
        attributes={
            "billing.username": username,
            "billing.amount": str(request.amount),
            "idempotency_key": x_idempotency_key,
        },
    ):
        result = await account_crud.idempotent_withdraw(x_idempotency_key, username, request.amount)
        if result.get("error") == "account_not_found":
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Account not found")
        return WithdrawResponse(success=result["success"], balance=result["balance"])
