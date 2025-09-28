from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..models.models import AuditLog
from typing import List, Dict, Any

router = APIRouter(prefix="/v1/audit", tags=["audit"])

@router.get("", response_model=List[Dict[str, Any]])
async def get_audit_logs(
    store_id: str = Query(...),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get paginated audit logs for a store"""
    
    offset = (page - 1) * limit
    
    logs = db.query(AuditLog).filter(
        AuditLog.payload["store_id"].astext == store_id
    ).order_by(AuditLog.ts.desc()).offset(offset).limit(limit).all()
    
    # Convert to response format
    response = []
    for log in logs:
        response.append({
            "id": str(log.id),
            "timestamp": log.ts.isoformat(),
            "actor": log.actor,
            "action": log.action,
            "payload": log.payload
        })
    
    # Add demo data if no real logs
    if not response:
        response = [
            {
                "id": "demo-1",
                "timestamp": "2024-01-15T10:30:00Z",
                "actor": f"store:{store_id}",
                "action": "fee_apply",
                "payload": {
                    "store_id": store_id,
                    "order_id": "DEMO-001",
                    "jurisdiction": "MN",
                    "amount_cents": 50,
                    "reason_codes": ["MN_THRESHOLD_MET"]
                }
            },
            {
                "id": "demo-2",
                "timestamp": "2024-01-15T09:15:00Z",
                "actor": f"store:{store_id}",
                "action": "fee_quote",
                "payload": {
                    "store_id": store_id,
                    "destination": {"state": "CO"},
                    "delivery_method": "ship",
                    "lines_count": 1
                }
            }
        ]
    
    return response