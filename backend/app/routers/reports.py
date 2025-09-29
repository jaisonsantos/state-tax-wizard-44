import io
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from ..core.deps import assert_store_access, get_current_user_email
from ..db.database import get_db
from ..services.report_service import ReportService

router = APIRouter(prefix="/v1/reports", tags=["reports"])


@router.get("/co/dr1786")
async def generate_co_dr1786(
    store_id: str = Query(...),
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user_email: str = Depends(get_current_user_email),
):
    """Generate Colorado DR-1786 CSV report"""

    assert_store_access(db, current_user_email, store_id)

    # Parse dates
    from_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
    to_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))

    # Generate CSV content
    csv_content = ReportService.generate_co_dr1786(store_id, from_dt, to_dt, db)

    # Return as downloadable CSV
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=co_dr1786_report.csv"},
    )


@router.get("/mn/summary")
async def generate_mn_summary(
    store_id: str = Query(...),
    from_date: str = Query(...),
    to_date: str = Query(...),
    format: str = Query(default="csv"),
    db: Session = Depends(get_db),
    current_user_email: str = Depends(get_current_user_email),
):
    """Generate Minnesota Summary report"""

    assert_store_access(db, current_user_email, store_id)

    # Parse dates
    from_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
    to_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))

    # Generate report content
    report_content = ReportService.generate_mn_summary(store_id, from_dt, to_dt, db, format)

    if format == "csv":
        return StreamingResponse(
            io.StringIO(report_content),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=mn_summary_report.csv"},
        )

    # JSON format
    return JSONResponse(content=report_content)
