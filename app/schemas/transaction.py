from pydantic import BaseModel, Field


class TransactionInput(BaseModel):
    transaction_id: str
    from_bank: str
    to_bank: str
    account_from: str
    account_to: str
    amount: float = Field(..., gt=0)
    currency: str
    payment_format: str
    timestamp: str | None = None


class AMLSimInput(BaseModel):
    transaction_id: str
    from_bank: str
    to_bank: str
    account_from: str
    account_to: str
    amount: float = Field(..., gt=0)
    currency: str
    payment_format: str
