import io
import json
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..core.deps import AuthContext, assert_store_access, get_auth_context
from ..db.database import get_db
from ..models.models import AuditLog, StoreSetting
from ..observability import ensure_request_id
from ..services.report_service import ReportExportResult, ReportService
from ..services.taxo_webhook_service import TaxoWebhookService

router = APIRouter(prefix="/v1/reports", tags=["reports"])


def _parse_iso_datetime(value: str) -> datetime:
    """Parse ISO8601 strings that may end with "Z" or contain offsets."""

    raw = value.strip()

    # Support epoch timestamps for convenience when debugging.
    try:
        if raw.replace(".", "", 1).lstrip("+-").isdigit():
            return datetime.fromtimestamp(float(raw), tz=timezone.utc)
    except ValueError:  # pragma: no cover - defensive guard
        pass

    if raw.endswith("Z"):
        core = raw[:-1]
        # Detect offsets such as +00:00 or -05:00.
        if len(core) >= 6 and core[-6] in {"+", "-"} and core[-3] == ":":
            raw = core
        else:
            raw = core + "+00:00"

    return datetime.fromisoformat(raw)


def _persist_audit(
    db: Session,
    *,
    actor: str,
    store_id: str,
    report: str,
    fmt: str,
    from_date: datetime,
    to_date: datetime,
    outcome: str,
    row_count: int,
    mime_type: str,
    error: str | None = None,
) -> None:
    payload: Dict[str, Any] = {
        "store_id": store_id,
        "report": report,
        "format": fmt,
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat(),
        "row_count": row_count,
        "outcome": outcome,
        "mime_type": mime_type,
        "subject": actor.removeprefix("user:"),
    }
    if error:
        payload["error"] = error

    audit_log = AuditLog(actor=actor, action="report_export", payload=payload)
    db.add(audit_log)
    db.flush()


@router.get("/co/dr1786")
async def generate_co_dr1786(
    http_request: Request,
    store_id: str = Query(...),
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Generate Colorado DR-1786 CSV report"""

    assert_store_access(db, auth, store_id)

    # Parse dates
    from_dt = _parse_iso_datetime(from_date)
    to_dt = _parse_iso_datetime(to_date)

    actor = f"user:{auth.email}"

    request_id = ensure_request_id(http_request.headers.get("x-request-id") if http_request else None)
    store_settings = (
        db.query(StoreSetting)
        .filter(StoreSetting.store_id == store_id)
        .first()
    )

    try:
        result = ReportService.generate_co_dr1786(store_id, from_dt, to_dt, db)
    except Exception as exc:  # pragma: no cover - defensive guard
        db.rollback()
        ReportService.observe_export(
            report="co_dr1786",
            jurisdiction="CO",
            store_id=store_id,
            fmt="csv",
            from_date=from_dt,
            to_date=to_dt,
            row_count=0,
            outcome="failure",
            error=str(exc),
        )
        _persist_audit(
            db,
            actor=actor,
            store_id=store_id,
            report="co_dr1786",
            fmt="csv",
            from_date=from_dt,
            to_date=to_dt,
            outcome="failure",
            row_count=0,
            mime_type="text/csv",
            error=str(exc),
        )
        db.commit()
        raise

    _persist_audit(
        db,
        actor=actor,
        store_id=store_id,
        report=result.report,
        fmt=result.format,
        from_date=from_dt,
        to_date=to_dt,
        outcome="success",
        row_count=result.row_count,
        mime_type="text/csv",
    )

    queued_events = []
    download_path = (
        f"/api/v1/reports/co/dr1786?store_id={store_id}"
        f"&from_date={from_dt.astimezone(timezone.utc).isoformat()}"
        f"&to_date={to_dt.astimezone(timezone.utc).isoformat()}"
    )
    queued = TaxoWebhookService.queue_report_ready(
        db,
        store_id=store_id,
        report=result.report,
        fmt=result.format,
        from_date=from_dt,
        to_date=to_dt,
        row_count=result.row_count,
        download_path=download_path,
        request_id=request_id,
    )
    if queued:
        queued_events.append(queued)

    db.commit()

    if queued_events:
        TaxoWebhookService.dispatch_events(
            db,
            store_id,
            queued_events,
            settings_model=store_settings,
        )
        db.commit()

    return StreamingResponse(
        io.StringIO(result.content if isinstance(result.content, str) else ""),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=co_dr1786_report.csv"},
    )


@router.get("/mn/summary")
async def generate_mn_summary(
    http_request: Request,
    store_id: str = Query(...),
    from_date: str = Query(...),
    to_date: str = Query(...),
    format: str = Query(default="csv"),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(get_auth_context),
):
    """Generate Minnesota Summary report"""

    assert_store_access(db, auth, store_id)

    from_dt = _parse_iso_datetime(from_date)
    to_dt = _parse_iso_datetime(to_date)

    actor = f"user:{auth.email}"
    requested_format = format.lower()
    request_id = ensure_request_id(http_request.headers.get("x-request-id"))
    store_settings = (
        db.query(StoreSetting)
        .filter(StoreSetting.store_id == store_id)
        .first()
    )

    if requested_format not in {"csv", "json"}:
        error_message = f"Unsupported format '{format}'. Use csv or json."
        ReportService.observe_export(
            report="mn_summary",
            jurisdiction="MN",
            store_id=store_id,
            fmt=requested_format,
            from_date=from_dt,
            to_date=to_dt,
            row_count=0,
            outcome="failure",
            error=error_message,
        )
        _persist_audit(
            db,
            actor=actor,
            store_id=store_id,
            report="mn_summary",
            fmt=requested_format,
            from_date=from_dt,
            to_date=to_dt,
            outcome="failure",
            row_count=0,
            mime_type="application/octet-stream",
            error=error_message,
        )
        db.commit()
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "loc": ["query", "format"],
                    "msg": error_message,
                    "type": "value_error",
                }
            ],
        )

    try:
        result: ReportExportResult = ReportService.generate_mn_summary(
            store_id, from_dt, to_dt, db, requested_format
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        db.rollback()
        ReportService.observe_export(
            report="mn_summary",
            jurisdiction="MN",
            store_id=store_id,
            fmt=requested_format,
            from_date=from_dt,
            to_date=to_dt,
            row_count=0,
            outcome="failure",
            error=str(exc),
        )
        _persist_audit(
            db,
            actor=actor,
            store_id=store_id,
            report="mn_summary",
            fmt=requested_format,
            from_date=from_dt,
            to_date=to_dt,
            outcome="failure",
            row_count=0,
            mime_type="application/octet-stream",
            error=str(exc),
        )
        db.commit()
        raise

    mime_type = "text/csv" if requested_format == "csv" else "application/json"

    _persist_audit(
        db,
        actor=actor,
        store_id=store_id,
        report=result.report,
        fmt=result.format,
        from_date=from_dt,
        to_date=to_dt,
        outcome="success",
        row_count=result.row_count,
        mime_type=mime_type,
    )

    queued_events = []
    download_path = (
        f"/api/v1/reports/mn/summary?store_id={store_id}"
        f"&from_date={from_dt.astimezone(timezone.utc).isoformat()}"
        f"&to_date={to_dt.astimezone(timezone.utc).isoformat()}"
        f"&format={requested_format}"
    )
    queued = TaxoWebhookService.queue_report_ready(
        db,
        store_id=store_id,
        report=result.report,
        fmt=result.format,
        from_date=from_dt,
        to_date=to_dt,
        row_count=result.row_count,
        download_path=download_path,
        request_id=request_id,
    )
    if queued:
        queued_events.append(queued)

    db.commit()

    if queued_events:
        TaxoWebhookService.dispatch_events(
            db,
            store_id,
            queued_events,
            settings_model=store_settings,
        )
        db.commit()

    if requested_format == "csv":
        return StreamingResponse(
            io.StringIO(result.content if isinstance(result.content, str) else ""),
            media_type=mime_type,
            headers={"Content-Disposition": "attachment; filename=mn_summary_report.csv"},
        )

    json_payload = json.dumps(result.content)
    filename = f"mn_summary_{from_dt:%Y%m%d}_{to_dt:%Y%m%d}.json"
    return StreamingResponse(
        io.StringIO(json_payload),
        media_type=mime_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )
