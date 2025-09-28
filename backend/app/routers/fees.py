import time
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..schema.fees import FeeQuoteRequest, FeeQuoteResponse, FeeApplyRequest, FeeApplyResponse
from ..services.fee_service import FeeCalculationService
from ..models.models import OrderFee, AuditLog, Store
from ..observability import (
    decision_latency_ms,
    fees_applied_total,
    log_fee_event,
    ensure_request_id,
)

router = APIRouter(prefix="/v1/fees", tags=["fees"])

@router.post("/quote", response_model=FeeQuoteResponse)
async def quote_fees(request: FeeQuoteRequest, db: Session = Depends(get_db)):
    """Calculate delivery fees for a given order"""
    
    # Verify store exists
    store = db.query(Store).filter(Store.id == request.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    
    # Calculate fees using the service
    lines = FeeCalculationService.calculate_fees(request, db)
    
    # Log the audit event
    audit_log = AuditLog(
        actor=f"store:{request.store_id}",
        action="fee_quote",
        payload={
            "store_id": request.store_id,
            "destination": request.destination.dict(),
            "delivery_method": request.delivery_method,
            "item_count": len(request.items),
            "shipping_amount_cents": request.shipping_amount_cents,
            "lines_count": len(lines)
        }
    )
    db.add(audit_log)
    db.commit()
    
    return FeeQuoteResponse(
        lines=lines,
        decided=True
    )

@router.post("/apply", response_model=FeeApplyResponse)
async def apply_fees(
    request: FeeApplyRequest,
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """Apply delivery fees to an order (idempotent)"""

    existing_lines = db.query(OrderFee).filter(
        OrderFee.store_id == request.store_id,
        OrderFee.order_id == request.order_id
    ).all()

    if existing_lines:
        lines = [
            {
                "jurisdiction": order_fee.jurisdiction,
                "amount_cents": order_fee.amount_cents,
                "display_name": "Delivery Fee",
                "rule_version": order_fee.rule_version,
                "reason_codes": order_fee.reason_codes or [],
            }
            for order_fee in existing_lines
        ]
        return FeeApplyResponse(success=True, lines=lines)

    # Calculate fees
    quote_request = FeeQuoteRequest(
        store_id=request.store_id,
        destination=request.destination,
        delivery_method=request.delivery_method,
        items=request.items,
        shipping_amount_cents=request.shipping_amount_cents
    )
    
    started = time.perf_counter()
    lines = FeeCalculationService.calculate_fees(quote_request, db)
    elapsed_ms = (time.perf_counter() - started) * 1000
    decision_latency_ms.observe(elapsed_ms)

    # Store the applied fees
    for line in lines:
        order_fee = OrderFee(
            store_id=request.store_id,
            order_id=request.order_id,
            jurisdiction=line.jurisdiction,
            amount_cents=line.amount_cents,
            delivery_method=request.delivery_method,
            absorbed=False,
            rule_version=line.rule_version,
            reason_codes=line.reason_codes,
        )
        db.add(order_fee)
        fees_applied_total.labels(jurisdiction=line.jurisdiction).inc()

    # Log the audit event
    audit_log = AuditLog(
        actor=f"store:{request.store_id}",
        action="fee_apply",
        payload={
            "store_id": request.store_id,
            "order_id": request.order_id,
            "delivery_method": request.delivery_method,
            "lines": [
                {
                    "jurisdiction": line.jurisdiction,
                    "amount_cents": line.amount_cents,
                    "reason_codes": line.reason_codes,
                    "rule_version": line.rule_version,
                }
                for line in lines
            ],
            "status": "applied",
        }
    )
    db.add(audit_log)

    db.commit()

    request_id = ensure_request_id(
        http_request.headers.get("x-request-id") if http_request else None
    )

    for line in lines:
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
            }
        )

    return FeeApplyResponse(
        success=True,
        lines=lines
    )