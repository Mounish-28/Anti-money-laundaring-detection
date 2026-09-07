from pydantic import BaseModel


class SAMLDInput(BaseModel):
    transaction_id: str
    sender_id: str
    receiver_id: str
    amount: float
    fan_in_count: int
    fan_out_count: int
    sender_velocity_24h: float
