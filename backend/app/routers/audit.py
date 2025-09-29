from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import AuditLog

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("", response_model=Dict[str, Any])
async def get_audit_logs(
    store_id: str = Query(...),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Get paginated audit logs for a store"""

    assert_store_access(db, auth, store_id)

    offset = (page - 1) * limit

    total = (
        db.query(func.count(AuditLog.id))
        .filter(AuditLog.payload["store_id"].astext == store_id)
        .scalar()
        or 0
    )

    logs = (
        db.query(AuditLog)
        .filter(AuditLog.payload["store_id"].astext == store_id)
        .order_by(AuditLog.ts.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Convert to response format
    items: List[Dict[str, Any]] = []
    for log in logs:
        items.append(
            {
                "id": str(log.id),
                "timestamp": log.ts.isoformat() if log.ts else None,
                "actor": log.actor,
                "action": log.action,
                "payload": log.payload,
            }
        )

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
    }
