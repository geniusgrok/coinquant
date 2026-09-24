from decimal import Decimal as D

from research.persistent_hold_replay import recoverable_budget


def test_recoverable_budget_leaves_space_for_later_decisions():
    assert recoverable_budget(D('100'), D('100')) == D('10')
    assert recoverable_budget(D('55'), D('100')) == D('2.5')
    assert recoverable_budget(D('50'), D('100')) == 0
    assert recoverable_budget(D('49'), D('100')) == 0
