from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class EllipticNodeInput(BaseModel):
    node_id: Optional[str] = None
    tx_hash: Optional[str] = None
    timestep: Optional[int] = 49
    features: List[float] = Field(..., min_length=166, max_length=166)
    btc_value: Optional[float] = None
    from_address: Optional[str] = None
    to_address: Optional[str] = None
    in_count: Optional[int] = None
    out_count: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def resolve_ids(cls, data):
        if isinstance(data, dict):
            nid = data.get("node_id") or data.get("tx_hash") or "btc_live_tx"
            data["node_id"] = nid
            data["tx_hash"] = nid
        return data
