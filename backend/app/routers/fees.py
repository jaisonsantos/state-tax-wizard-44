import hashlib
import hmac
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import AuditLog, OrderFee, Store, StoreSetting
from ..observability import (
    decision_latency_ms,
    ensure_request_id,
    fees_applied_total,
    fees_absorbed_total,
    log_fee_event,
)
from ..schema.fees import (
    FeeApplyRequest,
    FeeApplyResponse,
    FeeDecision,
    FeeLine,
    FeeQuoteRequest,
    FeeQuoteResponse,
    FeeReversalRequest,
    FeeReversalResponse,
)
from ..security.rate_limit import rate_limiter
from ..services.fee_service import (
    DEFAULT_LABELS,
    FeeCalculationResult,
    FeeCalculationService,
    _normalize_override,
)

router = APIRouter(prefix="/v1/fees", tags=["fees"])


def _record_latency(route: str, elapsed_ms: float, decisions: list[FeeDecision]) -> None:
    for decision in decisions:
        decision_latency_ms.labels(
            route=route,
            jurisdiction=decision.jurisdiction,
            outcome=decision.outcome,
        ).observe(elapsed_ms)


def _resolve_display_name(order_fee: OrderFee, settings: StoreSetting | None) -> str:
    if order_fee.display_name:
        return order_fee.display_name
    override = _normalize_override(settings.label_override if settings else None)
    if override:
        return override
    return DEFAULT_LABELS.get(order_fee.jurisdiction, "Delivery Fee")


def _enforce_hmac(signature: str | None, body: bytes, settings: StoreSetting | None) -> None:
    secret = (settings.hmac_secret or "").strip() if settings and settings.hmac_secret else ""
    if not secret:
        return

    if not signature:
        raise HTTPException(status_code=401, detail="Missing HMAC signature")

    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, digest):
        raise HTTPException(status_code=403, detail="Invalid HMAC signature")


@router.post("/quote", response_model=FeeQuoteResponse)
async def quote_fees(
    request: FeeQuoteRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Calculate delivery fees for a given order."""

    rate_limiter.check(auth.token, "quote")

    assert_store_access(db, auth, request.store_id)

    store = db.query(Store).filter(Store.id == request.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    started = time.perf_counter()
    result: FeeCalculationResult = FeeCalculationService.calculate_fees(request, db)
    elapsed_ms = (time.perf_counter() - started) * 1000
    _record_latency("quote", elapsed_ms, result.decisions)

    audit_log = AuditLog(
        actor=f"user:{auth.email}",
        action="fee_quote",
        payload={
            "store_id": request.store_id,
            "subject": auth.email,
            "destination": request.destination.dict(),
            "delivery_method": request.delivery_method,
            "item_count": len(request.items),
            "shipping_amount_cents": request.shipping_amount_cents,
            "lines_count": len(result.lines),
            "absorbed": result.absorbed,
            "source_of_remittance": request.source_of_remittance,
            "decisions": [decision.dict() for decision in result.decisions],
        },
    )
    db.add(audit_log)
    db.commit()

    return FeeQuoteResponse(
        lines=result.lines,
        decisions=result.decisions,
        decided=True,
        absorbed=result.absorbed,
    )


@router.post("/apply", response_model=FeeApplyResponse)
async def apply_fees(
    request: FeeApplyRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Apply delivery fees to an order (idempotent)."""

    rate_limiter.check(auth.token, "apply")

    assert_store_access(db, auth, request.store_id)

    settings = (
        db.query(StoreSetting)
        .filter(StoreSetting.store_id == request.store_id)
        .first()
    )

    raw_body = await http_request.body()
    _enforce_hmac(http_request.headers.get("x-rdf-signature"), raw_body, settings)

    existing_lines = db.query(OrderFee).filter(
        OrderFee.store_id == request.store_id,
        OrderFee.order_id == request.order_id,
        OrderFee.status == "applied",
    ).all()

    quote_request = FeeQuoteRequest(
        store_id=request.store_id,
        destination=request.destination,
        delivery_method=request.delivery_method,
        items=request.items,
        shipping_amount_cents=request.shipping_amount_cents,
        source_of_remittance=request.source_of_remittance,
    )

    started = time.perf_counter()
    result = FeeCalculationService.calculate_fees(quote_request, db)
    elapsed_ms = (time.perf_counter() - started) * 1000
    _record_latency("apply", elapsed_ms, result.decisions)

    if existing_lines:
        lines = [
            FeeLine(
                jurisdiction=order_fee.jurisdiction,
                amount_cents=order_fee.amount_cents,
                display_name=_resolve_display_name(order_fee, settings),
                rule_version=order_fee.rule_version,
                reason_codes=order_fee.reason_codes or [],
                absorbed=order_fee.absorbed,
            )
            for order_fee in existing_lines
        ]
        absorbed = any(order_fee.absorbed for order_fee in existing_lines)
        return FeeApplyResponse(
            success=True,
            lines=lines,
            decisions=result.decisions,
            absorbed=absorbed,
        )

    for line in result.lines:
        order_fee = OrderFee(
            store_id=request.store_id,
            order_id=request.order_id,
            jurisdiction=line.jurisdiction,
            amount_cents=line.amount_cents,
            delivery_method=request.delivery_method,
            absorbed=line.absorbed,
            rule_version=line.rule_version,
            reason_codes=line.reason_codes,
            display_name=line.display_name,
            status="applied",
            reversal_reason=None,
            source_of_remittance=request.source_of_remittance,
        )
        db.add(order_fee)
        fees_applied_total.labels(jurisdiction=line.jurisdiction).inc()
        if line.absorbed:
            fees_absorbed_total.labels(jurisdiction=line.jurisdiction).inc()

    audit_log = AuditLog(
        actor=f"user:{auth.email}",
        action="fee_apply",
        payload={
            "store_id": request.store_id,
            "subject": auth.email,
            "order_id": request.order_id,
            "delivery_method": request.delivery_method,
            "lines": [line.dict() for line in result.lines],
            "status": "applied" if result.lines else "skipped",
            "absorbed": result.absorbed,
            "source_of_remittance": request.source_of_remittance,
            "decisions": [decision.dict() for decision in result.decisions],
        },
    )
    db.add(audit_log)

    db.commit()

    request_id = ensure_request_id(http_request.headers.get("x-request-id"))

    for line in result.lines:
        log_fee_event(
            {
                "event": "fee_apply",
                "request_id": request_id,
                "store_id": request.store_id,
                "order_id": request.order_id,
                "jurisdiction": line.jurisdiction,
                "amount_cents": line.amount_cents,
                "reason_codes": line.reason_codes,
                "delivery_method": request.delivery_method,
                "absorbed": line.absorbed,
                "source_of_remittance": request.source_of_remittance,
                "subject": auth.email,
            }
        )

    return FeeApplyResponse(
        success=True,
        lines=result.lines,
        decisions=result.decisions,
        absorbed=result.absorbed,
    )


@router.post("/reverse", response_model=FeeReversalResponse)
async def reverse_fees(
    request: FeeReversalRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Reverse previously applied fees for an order."""

    rate_limiter.check(auth.token, "reverse")

    assert_store_access(db, auth, request.store_id)

    fees = (
        db.query(OrderFee)
        .filter(
            OrderFee.store_id == request.store_id,
            OrderFee.order_id == request.order_id,
        )
        .all()
    )

    if not fees:
        raise HTTPException(status_code=404, detail="No fees found for order")

    reversed_jurisdictions: list[str] = []
    refunded_amount = 0
    reversal_tag = f"REVERSAL_{request.reason}"

    now = datetime.utcnow()

    if request.reason == "DELIVERY_CANCELLED":
        for fee in fees:
            if fee.status == "reversed":
                continue
            fee.status = "reversed"
            fee.reversal_reason = request.reason
            fee.reversed_at = now
            reasons = list(fee.reason_codes or [])
            if reversal_tag not in reasons:
                reasons.append(reversal_tag)
            fee.reason_codes = reasons
            refunded_amount += fee.amount_cents
            reversed_jurisdictions.append(fee.jurisdiction)
    else:
        for fee in fees:
            fee.reversal_reason = request.reason
            reasons = list(fee.reason_codes or [])
            if reversal_tag not in reasons:
                reasons.append(reversal_tag)
            fee.reason_codes = reasons

    db.commit()

    request_id = ensure_request_id(http_request.headers.get("x-request-id"))
    for fee in fees:
        log_fee_event(
            {
                "event": "fee_reverse",
                "request_id": request_id,
                "store_id": request.store_id,
                "order_id": request.order_id,
                "jurisdiction": fee.jurisdiction,
                "amount_cents": fee.amount_cents,
                "status": fee.status,
                "reversal_reason": fee.reversal_reason,
                "subject": auth.email,
            }
        )

    audit_log = AuditLog(
        actor=f"user:{auth.email}",
        action="fee_reverse",
        payload={
            "store_id": request.store_id,
            "order_id": request.order_id,
            "reason": request.reason,
            "refunded_amount_cents": refunded_amount,
            "jurisdictions": reversed_jurisdictions,
        },
    )
    db.add(audit_log)
    db.commit()

    return FeeReversalResponse(
        success=True,
        refunded_amount_cents=refunded_amount,
        reversed_jurisdictions=reversed_jurisdictions,
        reason=request.reason,
    )
