from pydantic import BaseModel, Field, model_validator


class EllipticNodeInput(BaseModel):
    node_id: str | None = None
    tx_hash: str | None = None
    timestep: int | None = 49
    features: list[float] = Field(..., min_length=166, max_length=166)
    btc_value: float | None = None
    from_address: str | None = None
    to_address: str | None = None
    in_count: int | None = None
    out_count: int | None = None

    @model_validator(mode="before")
    @classmethod
    def resolve_ids(cls, data):
        if isinstance(data, dict):
            nid = data.get("node_id") or data.get("tx_hash") or "btc_live_tx"
            data["node_id"] = nid
            data["tx_hash"] = nid
        return data
