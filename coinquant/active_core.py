"""Frozen market-state and mother-risk rules for the active-core experiment.

Pure rules: the shared execution account remains the sole owner of fills, cash,
protection, and campaign consumption. No market data is fetched here.
"""
from decimal import Decimal as D


def coherent_trend(snapshot):
    """Require positive 7-, 28-, and 84-day completed trend components."""
    if snapshot is None or snapshot.opportunity is None:
        return None
    return snapshot.opportunity if len(snapshot.components) == 3 and all(
        component > 0 for component in snapshot.components) else None


def mother_stop_share(family, opportunity):
    """Maximum equity loss to frozen protection across all five entry slices."""
    if family == 'coherent_trend':
        return D('.08')
    if family == 'restart_budget':
        return D('.04') if opportunity.parent_identity is not None else D('.08')
    raise ValueError('unknown frozen active core')
