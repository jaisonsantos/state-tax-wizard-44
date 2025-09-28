from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..schema.fees import FeeQuoteRequest, FeeQuoteResponse, FeeApplyRequest, FeeApplyResponse
from ..services.fee_service import FeeCalculationService
from ..models.models import OrderFee, AuditLog, Store
from datetime import datetime
import uuid

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
async def apply_fees(request: FeeApplyRequest, db: Session = Depends(get_db)):
    """Apply delivery fees to an order (idempotent)"""
    
    # Check if already applied (idempotency)
    existing = db.query(OrderFee).filter(
        OrderFee.store_id == request.store_id,
        OrderFee.order_id == request.order_id
    ).first()
    
    if existing:
        # Return existing result
        return FeeApplyResponse(
            success=True,
            lines=[{
                "jurisdiction": existing.jurisdiction,
                "amount_cents": existing.amount_cents,
                "display_name": "Delivery Fee",
                "rule_version": existing.rule_version,
                "reason_codes": existing.reason_codes or []
            }]
        )
    
    # Calculate fees
    quote_request = FeeQuoteRequest(
        store_id=request.store_id,
        destination=request.destination,
        delivery_method=request.delivery_method,
        items=request.items,
        shipping_amount_cents=request.shipping_amount_cents
    )
    
    lines = FeeCalculationService.calculate_fees(quote_request, db)
    
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
            reason_codes=line.reason_codes
        )
        db.add(order_fee)
    
    # Log the audit event
    audit_log = AuditLog(
        actor=f"store:{request.store_id}",
        action="fee_apply",
        payload={
            "store_id": request.store_id,
            "order_id": request.order_id,
            "lines_applied": len(lines)
        }
    )
    db.add(audit_log)
    
    db.commit()
    
    return FeeApplyResponse(
        success=True,
        lines=lines
    )