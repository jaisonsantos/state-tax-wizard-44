from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class RuleVersionResponse(BaseModel):
    jurisdiction: str
    version: str
    effective_from: datetime
    effective_to: Optional[datetime] = None
    params: Dict[str, Any]
    is_latest: bool


class RulesResponse(BaseModel):
    rules: List[RuleVersionResponse]