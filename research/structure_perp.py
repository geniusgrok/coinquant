"""Research-only cash-priority short, with independent conservative risk caps."""
from contextlib import contextmanager
from decimal import Decimal as D
import hashlib
from pathlib import Path

from coinquant import campaign, linear_preview
from coinquant.campaign import disposition
from coinquant.linear_account import FEE
from coinquant.linear_sizing import GAP, FUNDING_RESERVE
from coinquant.types import Blocked
from research.complete_perp import ResearchCampaign, BaseCampaign, checksum

SPEC = Path(__file__).with_name('structure-spec.json')


class CashShort(ResearchCampaign):
    variant = 'cash-only-short'

    def __init__(self):
        super().__init__()
        self.decision_mark = None

    def short_active(self):
        primary = self.model.active
        if primary is None or primary.direction >= 0 or not self.trend(-1):
            return False
        if self.position_campaign is not None:
            return self.position_campaign == primary.identity
        incumbent = BaseCampaign.active.fget(self)
        consumed = self.macro_consumed if incumbent is self.macro_opportunity else self.primary_consumed
        # An already-consumed macro is not an incumbent BUY opportunity.
        return (disposition(incumbent, D(0), consumed) in ('flat', 'consumed') and
                primary.identity != self.primary_consumed)

    @property
    def active(self):
        if self.short_active():
            return self.model.active
        return BaseCampaign.active.fget(self)

    def macro_relevant(self):
        # Never suppress a required DFII10 read in order to manufacture cash.
        return BaseCampaign.macro_relevant(self)

    def select_macro(self, row, mark, call, *, bootstrap=False):
        BaseCampaign.select_macro(self, row, mark, call, bootstrap=bootstrap)
        mark = D(mark)
        if not mark.is_finite() or mark <= 0:
            raise Blocked('valid current mark required')
        self.decision_mark, self.decision_ms = mark, call

    def entry_fraction(self, friction):
        active = self.active
        if active is None or active.direction > 0:
            return BaseCampaign.entry_fraction(self, friction)
        mark = self.decision_mark
        if mark is None or active.stop <= mark:
            return D(0)
        reserve = active.stop / mark - 1 + GAP + FUNDING_RESERVE + 2*(FEE+D(friction))
        # These cap prospective sizing, not a guarantee against unbounded gaps.
        return min(self.fraction('1', friction), D('.5'), D('.01') / reserve)

    def checkpoint(self):
        saved = super().checkpoint()
        saved['body']['structure'] = {
            'spec_sha256': hashlib.sha256(SPEC.read_bytes()).hexdigest(),
            'decision_mark': str(self.decision_mark) if self.decision_mark is not None else None}
        saved['sha256'] = checksum(saved['body'])
        return saved

    @classmethod
    def restore(cls, saved):
        if saved.get('sha256') != checksum(saved['body']):
            raise Blocked('invalid structure checkpoint digest')
        body = dict(saved['body'])
        extra = body.pop('structure', {})
        if extra.get('spec_sha256') != hashlib.sha256(SPEC.read_bytes()).hexdigest():
            raise Blocked('foreign structure specification')
        result = super().restore({'body': body, 'sha256': checksum(body)})
        mark = extra.get('decision_mark')
        result.decision_mark = D(mark) if mark is not None else None
        if result.decision_mark is not None and (
                not result.decision_mark.is_finite() or result.decision_mark <= 0):
            raise Blocked('invalid saved decision mark')
        return result


@contextmanager
def variant():
    old = campaign.Campaign, linear_preview.Campaign
    try:
        campaign.Campaign = linear_preview.Campaign = CashShort
        yield
    finally:
        campaign.Campaign, linear_preview.Campaign = old
