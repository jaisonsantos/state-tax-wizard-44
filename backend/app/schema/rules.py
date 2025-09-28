from pydantic import BaseModel
from typing import List
from datetime import datetime

class RateScheduleItem(BaseModel):
    start: datetime
    end: datetime
    rate_cents: int

class CORule(BaseModel):
    rate_schedule: List[RateScheduleItem]

class MNRule(BaseModel):
    threshold_cents: int

class RulesResponse(BaseModel):
    mn: MNRule
    co: CORule