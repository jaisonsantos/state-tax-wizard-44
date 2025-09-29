import time

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import AuditLog, OrderFee, Store
from ..observability import (
    decision_latency_ms,
    ensure_request_id,
    fees_applied_total,
    log_fee_event,
)
from ..schema.fees import (
    FeeApplyRequest,
    FeeApplyResponse,
    FeeDecision,
    FeeLine,
    FeeQuoteRequest,
    FeeQuoteResponse,
)
from ..services.fee_service import FeeCalculationResult, FeeCalculationService

router = APIRouter(prefix="/v1/fees", tags=["fees"])


def _record_latency(operation: str, elapsed_ms: float, decisions: list[FeeDecision]) -> None:
    for decision in decisions:
        decision_latency_ms.labels(
            operation=operation,
            jurisdiction=decision.jurisdiction,
            outcome=decision.outcome,
        ).observe(elapsed_ms)


@router.post("/quote", response_model=FeeQuoteResponse)
async def quote_fees(
    request: FeeQuoteRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Calculate delivery fees for a given order."""

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

    assert_store_access(db, auth, request.store_id)

    existing_lines = db.query(OrderFee).filter(
        OrderFee.store_id == request.store_id,
        OrderFee.order_id == request.order_id,
    ).all()

    quote_request = FeeQuoteRequest(
        store_id=request.store_id,
        destination=request.destination,
        delivery_method=request.delivery_method,
        items=request.items,
        shipping_amount_cents=request.shipping_amount_cents,
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
                display_name="Delivery Fee",
                rule_version=order_fee.rule_version,
                reason_codes=order_fee.reason_codes or [],
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
            absorbed=result.absorbed,
            rule_version=line.rule_version,
            reason_codes=line.reason_codes,
        )
        db.add(order_fee)
        fees_applied_total.labels(jurisdiction=line.jurisdiction).inc()

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
                "absorbed": result.absorbed,
                "subject": auth.email,
            }
        )

    return FeeApplyResponse(
        success=True,
        lines=result.lines,
        decisions=result.decisions,
        absorbed=result.absorbed,
    )
