from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from coinquant.active_core import coherent_trend, mother_stop_share


def test_coherence_requires_all_three_completed_signs():
    opportunity=object()
    snapshot=SimpleNamespace(opportunity=opportunity,components=(D('.1'),D('.2'),D('.3')))
    assert coherent_trend(snapshot) is opportunity
    snapshot.components=(D('.1'),D('0'),D('.3'))
    assert coherent_trend(snapshot) is None
    assert coherent_trend(None) is None


def test_restart_child_has_smaller_aggregate_mother_stop_budget():
    parent=SimpleNamespace(parent_identity=None)
    child=SimpleNamespace(parent_identity=1577836800000)
    assert mother_stop_share('restart_budget',parent)==D('.08')
    assert mother_stop_share('restart_budget',child)==D('.04')
    assert mother_stop_share('coherent_trend',parent)==D('.08')
    with pytest.raises(ValueError):mother_stop_share('unknown',parent)
