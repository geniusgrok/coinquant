"""The frozen 20-observation DFII10 decline state for the SX60 overlay."""
from decimal import Decimal as D


def active(row):
    if row['missing_reason']:
        return False
    return D(row['latest_value']) <= D(row['prior20_value']) - D('.25')


def potential_hours(rows):
    """Conservatively request every positive call and the next exit-capable call."""
    hours = set()
    previous = False
    for row in rows:
        state = active(row)
        if state or previous:
            hours.add(row['call_time_ms'])
        previous = state
    return sorted(hours)
