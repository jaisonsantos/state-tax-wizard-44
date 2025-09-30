from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Text, cast, func
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
    action: Optional[str] = Query(default=None),
):
    """Get paginated audit logs for a store"""
    assert_store_access(db, auth, store_id)

    offset = (page - 1) * limit

    dialect_name = db.bind.dialect.name if db.bind else ""
    if dialect_name == "sqlite":
        store_filter = func.json_extract(AuditLog.payload, "$.store_id") == str(store_id)
    elif dialect_name == "postgresql":
        store_filter = AuditLog.payload["store_id"].astext == str(store_id)
    else:
        store_filter = cast(AuditLog.payload["store_id"], Text) == str(store_id)

    base_query = db.query(AuditLog).filter(store_filter)
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

    return {"items": items, "page": page, "limit": limit, "total": total}
