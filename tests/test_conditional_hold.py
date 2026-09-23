from decimal import Decimal as D
from types import SimpleNamespace
import unittest

from coinquant.conditional_hold import expiry_permission
from coinquant.multiscale import DAY


def op(identity, expires):
    return SimpleNamespace(identity=identity, expires=expires)


def state(published, score):
    return SimpleNamespace(available_at=published, score=score)


def test_only_original_expiry_and_published_positive_score():
    base=10*DAY;original=op(base,base+7*DAY)
    history={base+4*3600000:original,base+7*DAY:None}
    today=base+8*DAY+3600000
    signal={(base+8*DAY)+60000:state(base+8*DAY+60000,D('0.2'))}
    assert expiry_permission(original,today,history,signal)==(True,'expiry_positive_score')
    assert expiry_permission(original,base+DAY,history,signal)[0] is False
    assert expiry_permission(original,today,history,{} )==(False,'score_unavailable')
    signal[(base+8*DAY)+60000]=state(base+8*DAY+60000,D(0))
    assert expiry_permission(original,today,history,signal)==(False,'score_nonpositive')


def test_lost_opportunity_or_intervening_shock_is_not_expiry_only():
    original=op(10*DAY,17*DAY);now=19*DAY+3600000
    daily={19*DAY+60000:state(19*DAY+60000,D(1))}
    assert expiry_permission(original,now,{16*DAY:None},daily)[1]=='invalidated_before_expiry'
    assert expiry_permission(original,now,{17*DAY:None,18*DAY:op(18*DAY,25*DAY)},daily)[1]=='intervening_opportunity'


def test_offline_negative_then_positive_ends_existing_extension():
    original=op(10*DAY,17*DAY);now=20*DAY+3600000
    daily={19*DAY+60000:state(19*DAY+60000,D(-1)),
           20*DAY+60000:state(20*DAY+60000,D(1))}
    assert expiry_permission(original,now,{17*DAY:None},daily,last_checked=18*DAY)[1]=='offline_score_invalidated'


class ConditionalHoldTests(unittest.TestCase):
    test_expiry_and_publication = staticmethod(test_only_original_expiry_and_published_positive_score)
    test_other_invalidation = staticmethod(test_lost_opportunity_or_intervening_shock_is_not_expiry_only)
    test_offline_reversal = staticmethod(test_offline_negative_then_positive_ends_existing_extension)
