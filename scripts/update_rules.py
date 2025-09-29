#!/usr/bin/env python3
"""Load jurisdiction rule schedules into the database."""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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
            rows.append(
                {
                    "jurisdiction": row.get("jurisdiction", "CO"),
                    "version": row["version"],
                    "effective_from": _parse_dt(row["effective_from"]),
                    "effective_to": _parse_dt(row.get("effective_to") or None),
                    "params": {"rate_cents": int(row["rate_cents"])},
                }
            )
        return rows


def load_mn_rule(path: Path) -> Dict[str, Any]:
    with path.open() as handle:
        data = json.load(handle)
    return {
        "jurisdiction": "MN",
        "version": data["version"],
        "effective_from": _parse_dt(data["effective_from"]),
        "effective_to": _parse_dt(data.get("effective_to")),
        "params": {
            "threshold_cents": int(data["threshold_cents"]),
            "fee_cents": int(data["fee_cents"]),
        },
    }


def upsert_rule(db_session, rule_data: Dict[str, Any]) -> str:
    rule = (
        db_session.query(RuleVersion)
        .filter(
            RuleVersion.jurisdiction == rule_data["jurisdiction"],
            RuleVersion.version == rule_data["version"],
        )
        .first()
    )
    change = "none"
    if not rule:
        rule = RuleVersion(**rule_data)
        db_session.add(rule)
        change = "created"
    else:
        mutated = False
        for field in ("effective_from", "effective_to"):
            if getattr(rule, field) != rule_data[field]:
                setattr(rule, field, rule_data[field])
                mutated = True
        if rule.params != rule_data["params"]:
            rule.params = rule_data["params"]
            mutated = True
        if mutated:
            change = "updated"
    if change != "none":
        audit = AuditLog(
            actor="system:update_rules",
            action="rules.update",
            payload={
                "jurisdiction": rule_data["jurisdiction"],
                "version": rule_data["version"],
                "change": change,
            },
        )
        db_session.add(audit)
    return change


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
        for record in load_co_periods(args.co):
            result = upsert_rule(session, record)
            if result != "none":
                total_changes += 1
        mn_record = load_mn_rule(args.mn)
        result = upsert_rule(session, mn_record)
        if result != "none":
            total_changes += 1

        session.commit()
        print(f"Rules sync complete. {total_changes} change(s) applied.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
