from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from ..models.models import RuleVersion, StoreSetting
from ..schema.fees import FeeDecision, FeeLine, FeeQuoteRequest


DEFAULT_LABELS: Dict[str, str] = {
    "MN": "Road Improvement and Food Delivery Fee (MN)",
    "CO": "Retail Delivery Fee (CO)",
}


def _normalize_override(label: str | None) -> str:
    if not label:
        return ""
    cleaned = label.strip()
    if cleaned.lower() == "delivery fee":
        return ""
    return cleaned


@dataclass
class FeeCalculationResult:
    lines: List[FeeLine]
    decisions: List[FeeDecision]
    absorbed: bool


class FeeCalculationService:

    @staticmethod
    def calculate_fees(request: FeeQuoteRequest, db: Session) -> FeeCalculationResult:
        lines: List[FeeLine] = []
        decisions: List[FeeDecision] = []

        settings = (
            db.query(StoreSetting)
            .filter(StoreSetting.store_id == request.store_id)
            .first()
        )

        enable_mn = settings.enable_mn if settings else True
        enable_co = settings.enable_co if settings else True
        absorb_fee = settings.absorb_fee if settings else False
        label_override = _normalize_override(settings.label_override if settings else None)

        now = datetime.utcnow()
        mn_rule = (
            db.query(RuleVersion)
            .filter(
                RuleVersion.jurisdiction == "MN",
                RuleVersion.effective_from <= now,
                (RuleVersion.effective_to.is_(None))
                | (RuleVersion.effective_to > now),
            )
            .first()
        )

        co_rule = (
            db.query(RuleVersion)
            .filter(
                RuleVersion.jurisdiction == "CO",
                RuleVersion.effective_from <= now,
                (RuleVersion.effective_to.is_(None))
                | (RuleVersion.effective_to > now),
            )
            .first()
        )

        state = (request.destination.state or "").upper()
        delivery_method = request.delivery_method.lower()

        # Minnesota evaluation
        mn_decision = FeeDecision(
            jurisdiction="MN",
            outcome="skipped",
            reason_codes=[],
            amount_cents=0,
        )
        if not enable_mn:
            mn_decision.reason_codes.append("MN_DISABLED")
        elif state != "MN":
            mn_decision.reason_codes.append("MN_DEST_OUT_OF_STATE")
        elif delivery_method != "ship":
            if delivery_method in {"pickup", "curbside"}:
                mn_decision.reason_codes.append("MN_BOPIS_EXEMPT")
            else:
                mn_decision.reason_codes.append("MN_DELIVERY_METHOD_EXEMPT")
        elif not mn_rule:
            mn_decision.reason_codes.append("MN_RULE_NOT_FOUND")
        else:
            total_cents = sum(
                item.unit_price_cents * item.qty for item in request.items
            ) + request.shipping_amount_cents
            threshold_cents = mn_rule.params.get("threshold_cents", 10000)
            fee_cents = mn_rule.params.get("fee_cents", 50)

            if total_cents >= threshold_cents:
                line = FeeLine(
                    jurisdiction="MN",
                    amount_cents=fee_cents,
                    display_name=label_override or DEFAULT_LABELS["MN"],
                    rule_version=mn_rule.version,
                    reason_codes=["MN_THRESHOLD_MET"],
                    absorbed=absorb_fee,
                )
                lines.append(line)
                mn_decision.outcome = "applied"
                mn_decision.amount_cents = fee_cents
                mn_decision.reason_codes = line.reason_codes
            else:
                mn_decision.reason_codes.append("MN_UNDER_THRESHOLD")
        if not mn_decision.reason_codes:
            mn_decision.reason_codes.append("MN_NO_DECISION")
        decisions.append(mn_decision)

        # Colorado evaluation
        co_decision = FeeDecision(
            jurisdiction="CO",
            outcome="skipped",
            reason_codes=[],
            amount_cents=0,
        )
        base_reasons: List[str] = []

        if request.source_of_remittance == "marketplace":
            base_reasons.append("CO_MARKETPLACE_SOR")

        reasons = list(base_reasons)

        if not enable_co:
            reasons.append("CO_DISABLED")
        elif state != "CO":
            reasons.append("CO_DEST_OUT_OF_STATE")
        elif delivery_method != "ship":
            reasons.append("CO_DELIVERY_METHOD_EXEMPT")
        elif not co_rule:
            reasons.append("CO_RULE_NOT_FOUND")
        else:
            has_taxable = any(item.taxability == "taxable" for item in request.items)
            if has_taxable:
                rate_cents = co_rule.params.get("rate_cents", 28)
                line_reasons = ["CO_HAS_TAXABLE_ITEM", *base_reasons]
                line = FeeLine(
                    jurisdiction="CO",
                    amount_cents=rate_cents,
                    display_name=label_override or DEFAULT_LABELS["CO"],
                    rule_version=co_rule.version,
                    reason_codes=line_reasons,
                    absorbed=absorb_fee,
                )
                lines.append(line)
                co_decision.outcome = "applied"
                co_decision.amount_cents = rate_cents
                co_decision.reason_codes = line.reason_codes
            else:
                reasons.append("CO_NO_TAXABLE_ITEMS")

        if co_decision.outcome == "skipped":
            if not reasons:
                reasons.append("CO_NO_DECISION")
            co_decision.reason_codes = reasons
        elif base_reasons:
            # Ensure marketplace flag is present in the decision payload
            for code in base_reasons:
                if code not in co_decision.reason_codes:
                    co_decision.reason_codes.append(code)

        if not co_decision.reason_codes:
            co_decision.reason_codes.append("CO_NO_DECISION")
        decisions.append(co_decision)

        absorbed = absorb_fee and bool(lines)

        return FeeCalculationResult(lines=lines, decisions=decisions, absorbed=absorbed)