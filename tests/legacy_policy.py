"""Explicit historical SX60 fixture scope; the actual default is tested separately."""
from unittest.mock import patch
from coinquant.campaign import Campaign


def legacy_policy():
    fixture = patch('coinquant.linear_preview.Campaign', Campaign)
    return fixture.start, fixture.stop
