from decimal import Decimal as D
from types import SimpleNamespace

import pytest

from coinquant.active_core import coherent_trend, mother_stop_share, short_campaigns


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


def test_negative_daily_campaign_consumes_once_and_rearms_only_after_reset():
    def state(*values):return SimpleNamespace(components=tuple(map(D,values)))
    s={100:state(-1,-1,-1),200:state(-1,-.1,-1),300:state(-1,0,-1),
       400:state(-1,-1,-1),500:state(-1,-1,-1),600:state(-1,1,-1)}
    assert short_campaigns(s)=={100:-100,200:-100,300:None,400:-400,500:-400,600:None}
    long=SimpleNamespace(direction=1,parent_identity=None)
    short=SimpleNamespace(direction=-1,parent_identity=None)
    assert mother_stop_share('restart_uncapped',long) is None
    assert mother_stop_share('restart_uncapped',SimpleNamespace(parent_identity=7))==D('.04')
    assert mother_stop_share('short_2',short)==D('.02')
    assert mother_stop_share('short_4',short)==D('.04')
    assert mother_stop_share('short_4',long) is None
