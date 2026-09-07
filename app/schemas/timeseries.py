from pydantic import BaseModel


class TimeSeriesInput(BaseModel):
    account_id: str
    amount: float
    ema_1h: float
    ema_24h: float
    ema_7d: float
    delta_t_seconds: float
    burstiness_index: float
    sin_hour: float
    cos_hour: float
    sin_dow: float
    cos_dow: float
