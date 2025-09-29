from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..core.deps import get_current_user_email
from ..db.database import get_db
from ..models.models import RuleVersion
from ..schema.rules import RuleVersionResponse, RulesResponse

router = APIRouter(prefix="/v1/rules", tags=["rules"])


@router.get("", response_model=RulesResponse)
async def get_rules(
    db: Session = Depends(get_db),
    current_user_email: str = Depends(get_current_user_email),
):
    """Get all published rules for MN and CO, including effective windows."""

    rules = (
        db.query(RuleVersion)
        .order_by(RuleVersion.jurisdiction, RuleVersion.effective_from)
        .all()
    )

    latest_per_jurisdiction: dict[str, RuleVersion] = {}
    for rule in rules:
        current = latest_per_jurisdiction.get(rule.jurisdiction)
        if not current or (current.effective_from or datetime.min) < (rule.effective_from or datetime.min):
            latest_per_jurisdiction[rule.jurisdiction] = rule

    response = [
        RuleVersionResponse(
            jurisdiction=rule.jurisdiction,
            version=rule.version,
            effective_from=rule.effective_from,
            effective_to=rule.effective_to,
            params=rule.params,
            is_latest=latest_per_jurisdiction.get(rule.jurisdiction) == rule,
        )
        for rule in rules
    ]

    return RulesResponse(rules=response)
