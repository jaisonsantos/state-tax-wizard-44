from datetime import datetime, timezone


def test_clock_is_timezone_aware():
    now = datetime.now(timezone.utc)
    assert now.tzinfo is not None
