from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, Union
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from ..models.models import AuditLog


@dataclass
class AuditLogRecord:
    id: UUID
    ts: datetime
    actor: str
    action: str
    payload: dict


class AuditCursor:
    """Cursor serializer for keyset pagination over audit logs."""

    @staticmethod
    def encode(ts: datetime, log_id: UUID) -> str:
        raw = f"{ts.isoformat()}::{log_id}".encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii")

    @staticmethod
    def decode(cursor: str) -> Tuple[datetime, UUID]:
        decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        ts_raw, id_raw = decoded.split("::", 1)
        return datetime.fromisoformat(ts_raw), UUID(id_raw)


class AuditLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def store_filter(self, store_id: str):
        dialect_name = self.db.bind.dialect.name if self.db.bind else ""
        if dialect_name == "sqlite":
            return func.json_extract(AuditLog.payload, "$.store_id") == str(store_id)
        if dialect_name == "postgresql":
            return AuditLog.payload["store_id"].astext == str(store_id)
        return AuditLog.payload["store_id"].astext == str(store_id)

    def fetch(
        self,
        *,
        store_id: str,
        action: Optional[str] = None,
        actions: Optional[Union[List[str], Tuple[str, ...]]] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> Tuple[List[AuditLogRecord], Optional[str]]:
        if limit <= 0:
            return [], None

        query = self.db.query(AuditLog).filter(self.store_filter(store_id))
        if action and actions:
            raise ValueError("Specify either 'action' or 'actions', not both.")

        if action:
            query = query.filter(AuditLog.action == action)
        elif actions:
            query = query.filter(AuditLog.action.in_(list(actions)))

        if cursor:
            cursor_ts, cursor_id = AuditCursor.decode(cursor)
            query = query.filter(
                or_(
                    AuditLog.ts < cursor_ts,
                    and_(AuditLog.ts == cursor_ts, AuditLog.id < cursor_id),
                )
            )

        logs = (
            query.order_by(AuditLog.ts.desc(), AuditLog.id.desc())
            .limit(limit + 1)
            .all()
        )

        items = [
            AuditLogRecord(
                id=log.id,
                ts=log.ts,
                actor=log.actor,
                action=log.action,
                payload=log.payload,
            )
            for log in logs[:limit]
        ]

        next_cursor: Optional[str] = None
        if len(logs) > limit:
            tail = logs[limit]
            next_cursor = AuditCursor.encode(tail.ts, tail.id)

        return items, next_cursor

    @staticmethod
    def encode_cursor_from_model(log: Union[AuditLog, AuditLogRecord]) -> str:
        return AuditCursor.encode(log.ts, log.id)
