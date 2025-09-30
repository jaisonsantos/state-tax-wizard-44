from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import AuditLog
from ..services.audit_repository import AuditLogRepository

router = APIRouter(prefix="/v1/audit", tags=["audit"])


@router.get("", response_model=Dict[str, Any])
async def get_audit_logs(
    store_id: str = Query(...),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
    action: Optional[str] = Query(default=None),
):
    """Get paginated audit logs for a store"""
    assert_store_access(db, auth, store_id)

    repo = AuditLogRepository(db)

    if cursor:
        records, next_cursor = repo.fetch(
            store_id=store_id, action=action, limit=limit, cursor=cursor
        )
        items = [
            {
                "id": str(log.id),
                "timestamp": log.ts.isoformat() if log.ts else None,
                "actor": log.actor,
                "action": log.action,
                "payload": log.payload,
            }
            for log in records
        ]

        return {
            "items": items,
            "page": None,
            "limit": limit,
            "total": None,
            "next_cursor": next_cursor,
        }

    # Offset pagination retained for legacy consumers
    offset = (page - 1) * limit

    base_query = db.query(AuditLog).filter(repo.store_filter(store_id))
    if action:
        base_query = base_query.filter(AuditLog.action == action)

    total = int(base_query.order_by(None).count())
    logs = (
        base_query.order_by(AuditLog.ts.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items: List[Dict[str, Any]] = [
        {
            "id": str(log.id),
            "timestamp": log.ts.isoformat() if log.ts else None,
            "actor": log.actor,
            "action": log.action,
            "payload": log.payload,
        }
        for log in logs
    ]

    return {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "next_cursor": None,
    }
