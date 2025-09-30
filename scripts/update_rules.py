#!/usr/bin/env python3
"""Load jurisdiction rule schedules into the database."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.append(str(BACKEND_PATH))

from app.db.database import SessionLocal  # noqa: E402
from app.models.models import AuditLog, RuleVersion  # noqa: E402

CO_PERIODS_PATH = ROOT / "docs" / "rules" / "co_periods.csv"
MN_RULE_PATH = ROOT / "docs" / "rules" / "mn_threshold.json"


def _parse_dt(raw: str | None) -> Optional[datetime]:
    if not raw:
        return None
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))


def load_co_periods(path: Path) -> List[Dict[str, Any]]:
    with path.open() as handle:
        reader = csv.DictReader(handle)
        rows: List[Dict[str, Any]] = []
        for row in reader:
            effective_from = _parse_dt(row["effective_from"])
            effective_to = _parse_dt(row.get("effective_to") or None)
            rows.append(
                {
                    "jurisdiction": row.get("jurisdiction", "CO"),
                    "version": row["version"],
                    "effective_from": effective_from,
                    "effective_to": effective_to,
                    "params": {
                        "rate_cents": int(row["rate_cents"]),
                        "window": {
                            "effective_from": effective_from.isoformat() if effective_from else None,
                            "effective_to": effective_to.isoformat() if effective_to else None,
                        },
                    },
                }
            )
        return rows


def load_mn_rule(path: Path) -> Dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    effective_from = _parse_dt(data["effective_from"])
    effective_to = _parse_dt(data.get("effective_to"))
    params = {
        "threshold_cents": int(data["threshold_cents"]),
        "fee_cents": int(data["fee_cents"]),
    }
    if "active" in data:
        params["active"] = bool(data["active"])
    return {
        "jurisdiction": "MN",
        "version": data["version"],
        "effective_from": effective_from,
        "effective_to": effective_to,
        "params": params,
    }


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _diff_dict(existing: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    diff: Dict[str, Dict[str, Any]] = {}
    keys = set(existing.keys()) | set(new.keys())
    for key in sorted(keys):
        old = existing.get(key)
        new_value = new.get(key)
        if old != new_value:
            diff[key] = {"old": _serialize_value(old), "new": _serialize_value(new_value)}
    return diff


def upsert_rule(db_session, rule_data: Dict[str, Any]) -> Tuple[str, RuleVersion]:
    rule = (
        db_session.query(RuleVersion)
        .filter(
            RuleVersion.jurisdiction == rule_data["jurisdiction"],
            RuleVersion.version == rule_data["version"],
        )
        .first()
    )
    change = "none"
    payload_details: Dict[str, Any] = {
        "jurisdiction": rule_data["jurisdiction"],
        "version": rule_data["version"],
    }
    if not rule:
        rule = RuleVersion(**rule_data)
        db_session.add(rule)
        change = "created"
        payload_details.update(
            {
                "effective_from": _serialize_value(rule_data["effective_from"]),
                "effective_to": _serialize_value(rule_data["effective_to"]),
                "params": rule_data["params"],
            }
        )
    else:
        mutated = False
        diff: Dict[str, Dict[str, Any]] = {}
        for field in ("effective_from", "effective_to"):
            if getattr(rule, field) != rule_data[field]:
                diff[field] = {
                    "old": _serialize_value(getattr(rule, field)),
                    "new": _serialize_value(rule_data[field]),
                }
                setattr(rule, field, rule_data[field])
                mutated = True
        if rule.params != rule_data["params"]:
            diff["params"] = _diff_dict(rule.params or {}, rule_data["params"])
            rule.params = rule_data["params"]
            mutated = True
        if mutated:
            change = "updated"
            payload_details["diff"] = diff
    if change != "none":
        audit = AuditLog(
            actor="system:update_rules",
            action="rules.update",
            payload={**payload_details, "change": change},
        )
        db_session.add(audit)
    return change, rule


def reconcile_co_windows(db_session, records: List[Dict[str, Any]]) -> int:
    """Ensure historical Colorado periods are end-dated when new windows arrive."""

    total_changes = 0
    sorted_records = sorted(records, key=lambda item: item["effective_from"] or datetime.min)
    previous_rule: RuleVersion | None = None

    for index, record in enumerate(sorted_records):
        change, rule = upsert_rule(db_session, record)
        if change != "none":
            total_changes += 1

        # update the previous window to end right before the current window starts
        if previous_rule and record["effective_from"]:
            desired_end = record["effective_from"]
            if previous_rule.effective_to != desired_end:
                audit = AuditLog(
                    actor="system:update_rules",
                    action="rules.window_adjust",
                    payload={
                        "jurisdiction": previous_rule.jurisdiction,
                        "version": previous_rule.version,
                        "previous": _serialize_value(previous_rule.effective_to),
                        "new": _serialize_value(desired_end),
                    },
                )
                previous_rule.effective_to = desired_end
                db_session.add(audit)
                total_changes += 1

        previous_rule = rule

    # ensure latest window is open-ended
    if previous_rule and previous_rule.effective_to is not None:
        audit = AuditLog(
            actor="system:update_rules",
            action="rules.window_adjust",
            payload={
                "jurisdiction": previous_rule.jurisdiction,
                "version": previous_rule.version,
                "previous": _serialize_value(previous_rule.effective_to),
                "new": None,
            },
        )
        previous_rule.effective_to = None
        db_session.add(audit)
        total_changes += 1

    return total_changes


def main() -> None:
    parser = argparse.ArgumentParser(description="Load CO and MN rule schedules")
    parser.add_argument(
        "--co",
        type=Path,
        default=CO_PERIODS_PATH,
        help="Path to the Colorado rate schedule CSV",
    )
    parser.add_argument(
        "--mn",
        type=Path,
        default=MN_RULE_PATH,
        help="Path to the Minnesota threshold JSON",
    )
    args = parser.parse_args()

    if not args.co.exists():
        raise SystemExit(f"Colorado schedule file not found: {args.co}")
    if not args.mn.exists():
        raise SystemExit(f"Minnesota rule file not found: {args.mn}")

    session = SessionLocal()
    try:
        total_changes = 0
        co_records = load_co_periods(args.co)
        total_changes += reconcile_co_windows(session, co_records)

        mn_record = load_mn_rule(args.mn)
        change, _ = upsert_rule(session, mn_record)
        if change != "none":
            total_changes += 1

        session.commit()
        print(f"Rules sync complete. {total_changes} change(s) applied.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
