from typing import List
from ..schema.fees import FeeQuoteRequest, FeeLine, FeeItem
from ..models.models import RuleVersion
from sqlalchemy.orm import Session
from datetime import datetime

class FeeCalculationService:
    
    @staticmethod
    def calculate_fees(request: FeeQuoteRequest, db: Session) -> List[FeeLine]:
        lines = []
        
        # Get current rule versions
        mn_rule = db.query(RuleVersion).filter(
            RuleVersion.jurisdiction == "MN",
            RuleVersion.effective_from <= datetime.utcnow(),
            (RuleVersion.effective_to.is_(None)) | (RuleVersion.effective_to > datetime.utcnow())
        ).first()
        
        co_rule = db.query(RuleVersion).filter(
            RuleVersion.jurisdiction == "CO",
            RuleVersion.effective_from <= datetime.utcnow(),
            (RuleVersion.effective_to.is_(None)) | (RuleVersion.effective_to > datetime.utcnow())
        ).first()
        
        # Minnesota logic
        if request.destination.state == "MN" and mn_rule:
            if request.delivery_method in ["ship"]:  # Only shipping applies
                # Calculate total eligible amount (items + shipping)
                total_cents = sum(item.unit_price_cents * item.qty for item in request.items) + request.shipping_amount_cents
                threshold_cents = mn_rule.params.get("threshold_cents", 10000)
                
                if total_cents >= threshold_cents:
                    lines.append(FeeLine(
                        jurisdiction="MN",
                        amount_cents=50,  # $0.50
                        display_name="Minnesota Delivery Fee",
                        rule_version=mn_rule.version,
                        reason_codes=["MN_THRESHOLD_MET"]
                    ))
                else:
                    # Below threshold - no fee but log reason
                    pass
            elif request.delivery_method in ["pickup", "curbside"]:
                # BOPIS/curbside exempt
                pass
        
        # Colorado logic
        if request.destination.state == "CO" and co_rule:
            if request.delivery_method in ["ship"]:  # Only shipping applies
                # Check if there are taxable items
                has_taxable = any(item.taxability == "taxable" for item in request.items)
                
                if has_taxable:
                    # Get current rate from schedule
                    rate_cents = co_rule.params.get("rate_cents", 28)  # Default $0.28
                    
                    lines.append(FeeLine(
                        jurisdiction="CO",
                        amount_cents=rate_cents,
                        display_name="Colorado Delivery Fee",
                        rule_version=co_rule.version,
                        reason_codes=["CO_HAS_TAXABLE_ITEM"]
                    ))
        
        return lines