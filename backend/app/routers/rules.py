from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..schema.rules import RulesResponse, MNRule, CORule, RateScheduleItem
from ..models.models import RuleVersion
from datetime import datetime

router = APIRouter(prefix="/v1/rules", tags=["rules"])

@router.get("", response_model=RulesResponse)
async def get_rules(db: Session = Depends(get_db)):
    """Get current active rules for MN and CO"""
    
    # Get current MN rule
    mn_rule = db.query(RuleVersion).filter(
        RuleVersion.jurisdiction == "MN",
        RuleVersion.effective_from <= datetime.utcnow(),
        (RuleVersion.effective_to.is_(None)) | (RuleVersion.effective_to > datetime.utcnow())
    ).first()
    
    # Get current CO rule
    co_rule = db.query(RuleVersion).filter(
        RuleVersion.jurisdiction == "CO",
        RuleVersion.effective_from <= datetime.utcnow(),
        (RuleVersion.effective_to.is_(None)) | (RuleVersion.effective_to > datetime.utcnow())
    ).first()
    
    # Default values if no rules found
    mn_threshold = 10000  # $100.00
    co_rate = 28  # $0.28
    
    if mn_rule:
        mn_threshold = mn_rule.params.get("threshold_cents", 10000)
    
    if co_rule:
        co_rate = co_rule.params.get("rate_cents", 28)
    
    return RulesResponse(
        mn=MNRule(threshold_cents=mn_threshold),
        co=CORule(rate_schedule=[
            RateScheduleItem(
                start=datetime(2024, 1, 1),
                end=datetime(2024, 12, 31),
                rate_cents=co_rate
            )
        ])
    )