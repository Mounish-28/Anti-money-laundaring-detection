from typing import Optional
from pydantic import BaseModel, Field


class SAMLDInput(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction identifier")
    sender_id: str = Field(default="ACC_SENDER", description="Sender account/entity ID")
    receiver_id: str = Field(default="ACC_RECEIVER", description="Receiver account/entity ID")
    amount: float = Field(..., ge=0.0, description="Transaction amount (>= 0.0)")
    fan_in_count: int = Field(default=1, ge=0, description="Incoming ledger degree")
    fan_out_count: int = Field(default=1, ge=0, description="Outgoing ledger degree")
    sender_velocity_24h: float = Field(default=0.0, ge=0.0, description="24-hour cumulative sender velocity")
    payment_type: str = Field(default="ACH", description="Payment rail / instrument")
    sender_bank_location: str = Field(default="UK", description="Sender bank country code")
    receiver_bank_location: str = Field(default="UK", description="Receiver bank country code")
    payment_currency: str = Field(default="UK pounds", description="Originating payment currency")
    received_currency: str = Field(default="UK pounds", description="Beneficiary received currency")

