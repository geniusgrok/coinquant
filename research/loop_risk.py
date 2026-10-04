"""Joint actual-ledger valuation, explicit minute/path limits and risk plans."""
from collections import defaultdict
from datetime import datetime,timezone
from decimal import Decimal as D

from research import nine_routes as r, flow_risk as f

MINUTE=60000


def closes(pair):
    spot={int(t):row for t,row in pair['accounts']['spot']['daily'].items() if row['timestamp_ms']==int(t)+r.DAY}
    coin={int(datetime.fromisoformat(row['date']).replace(tzinfo=timezone.utc).timestamp()*1000):row
          for row in pair['accounts']['coin']['daily']
          if row['stamp_ms']==int(datetime.fromisoformat(row['date']).replace(tzinfo=timezone.utc).timestamp()*1000)+r.DAY}
    rows=[]
    for day in sorted(set(spot)&set(coin)):
        if pair['window'][0]-r.DAY<=day<pair['window'][1]:
            rows.append(dict(at_ms=day+r.DAY,equity_cny=D(spot[day]['equity_cny'])+D(coin[day]['equity_cny']),
                             equity_usdt=D(spot[day]['equity_usdt'])+D(coin[day]['equity_usdt'])))
    return rows


def drawdown(rows,initial=D(10000)):
    peak=initial;mdd=D(0);underwater=longest=0
    previous=-1
    for row in rows:
        if row['at_ms']<=previous:raise ValueError('joint risk samples must be strictly chronological')
        previous=row['at_ms']
        value=r.number(row['equity_cny'])
        if value<=0:raise ValueError('nonpositive original joint equity')
        peak=max(peak,value);mdd=max(mdd,1-value/peak)
        underwater=underwater+1 if value<peak else 0;longest=max(longest,underwater)
    return dict(mdd=str(mdd),samples=len(rows),longest_underwater_samples=longest)


class Wallets:
    def __init__(self,pair):
        self.spot_cash=D(pair['accounts']['spot']['initial_usdt']);self.spot_q=D(0)
        self.coin_cash=D(pair['accounts']['coin']['initial_usdt']);self.coin_q=D(0);self.entry=D(0)
        self.events=defaultdict(list)
        for row in pair['accounts']['spot']['fills']:self.events[row['time']].append(('spot',row))
        for row in pair['accounts']['coin']['trades']:self.events[row['time']].append(('coin',row))
        for row in pair['accounts']['coin']['funding_ledger']:
            if row['asset']!='USDT' or row['symbol']!='BTCUSDT':raise ValueError('foreign account income')
            self.events[row['time']].append(('income',row))
        self.times=iter(sorted(self.events));self.next=next(self.times,None)

    def amounts(self):return self.spot_cash,self.spot_q,self.coin_cash,self.coin_q,self.entry

    def advance(self,through):
        states=[self.amounts()]
        while self.next is not None and self.next<=through:
            for kind,row in self.events[self.next]:
                if kind=='spot':
                    q,quote,fee=map(r.number,(row['qty'],row['quote'],row['commission']))
                    sign=1 if row['buyer'] else -1
                    if row['commission_asset'] not in ('BTC','USDT'):raise ValueError('foreign Spot commission')
                    self.spot_q+=sign*q-(fee if row['commission_asset']=='BTC' else 0)
                    self.spot_cash-=sign*quote+(fee if row['commission_asset']=='USDT' else 0)
                elif kind=='coin':
                    q,price=map(r.number,(row['qty'],row['price']))
                    if row['side']=='BUY':
                        self.entry=(self.coin_q*self.entry+q*price)/(self.coin_q+q);self.coin_q+=q
                    elif row['side']=='SELL':self.coin_q-=q
                    else:raise ValueError('unknown Coin fill side')
                else:self.coin_cash+=r.number(row['income'])
            if self.spot_q<D('-1e-20') or self.coin_q<0:raise ValueError('unowned or short reconstructed wallet')
            states.append(self.amounts());self.next=next(self.times,None)
        return states

    @staticmethod
    def equity(state,spot_price,mark):
        cash,q,wallet,position,entry=state
        return cash+q*spot_price+wallet+(position*(mark-entry) if position else 0)


def joint_risk(pair,bars,marks,fx):
    """Same old fills. Deterministic Spot proxy plus official mark-minute bounds.

    It does not replace the old venue or infer native account execution.
    """
    begin,end=pair['window'];wallet=Wallets(pair);samples=[];peak_upper=D(10000);upper_mdd=D(0)
    missing=missing_held=0;expected=(end-begin)//MINUTE
    wallet.advance(begin)
    for stamp in range(begin+MINUTE,end+1,MINUTE):
        states=wallet.advance(stamp);row=marks.get(stamp-MINUTE)
        needs_mark=any(state[3] for state in states)
        if row is None and needs_mark:
            missing+=1;missing_held+=1;continue
        if row is None:missing+=1
        before=f.price_at(bars,stamp-MINUTE);close=f.price_at(bars,stamp-1)
        mark=row[3] if row is not None else D(0)
        current=Wallets.equity(wallet.amounts(),close,mark)*fx(stamp)*D('.999')
        samples.append(dict(at_ms=stamp,equity_cny=current))
        lo,hi=(row[2],row[1]) if row is not None else (D(0),D(0))
        lower=min(Wallets.equity(state,min(before,close),lo) for state in states)*fx(stamp)*D('.999')
        upper=max(Wallets.equity(state,max(before,close),hi) for state in states)*fx(stamp)*D('.999')
        peak_upper=max(peak_upper,upper);upper_mdd=max(upper_mdd,1-lower/peak_upper)
    daily=closes(pair);daily_result=drawdown(daily)
    final=pair['accounts'];residual=dict(spot_cash=str(wallet.spot_cash-D(final['spot']['cash_usdt'])),
        spot_btc=str(wallet.spot_q-D(final['spot']['btc'])),coin_btc=str(wallet.coin_q-D(final['coin']['position'])),
        coin_equity=str(wallet.coin_cash+wallet.coin_q*(D(final['coin']['final_mark'])-wallet.entry)-D(final['coin']['final_usdt'])))
    if any(abs(D(v))>D('1e-8') for v in residual.values()):raise ValueError('reconstruction disagrees with accepted final wallet')
    minute_result=drawdown(samples)
    return dict(daily_close=daily_result,minute_close=minute_result,
        minute_expected=expected,missing_official_mark_minutes=missing,missing_held_minutes=missing_held,
        source_proxy_mdd_lower_bound=max(D(daily_result['mdd']),D(minute_result['mdd'])),
        source_proxy_mdd_upper_bound=upper_mdd if not missing_held else None,
        minute_bounds_complete=not missing_held,final_wallet_residual=residual,
        original_session_observed_mdd=pair['synchronized_observed_mdd'],
        continuous_native_mdd_verified=False,new_accounts=0,original_fills_unchanged=True,
        meaning='Original synthetic Spot high-before-low marks, actual ledger fills and income, official Coin minute mark intervals. Conservative source path envelope; not native/shared real-price execution.')


def price_revaluation(pair,bars,spot_minutes,marks,fx):
    """Test the valuation consequence of the old daily proxy on selected months.

    Old fills are held fixed. This is a sensitivity diagnostic, not a new wallet
    or evidence those fills/protection would occur at the real spot prices.
    """
    begin,end=pair['window'];wallet=Wallets(pair);selected=[];maximum=D(0);missing=0
    for stamp,bar in sorted(spot_minutes.items()):
        if not begin<=stamp<end:continue
        wallet.advance(stamp+MINUTE);mark=marks.get(stamp)
        if mark is None and wallet.coin_q:missing+=1;continue
        equity=Wallets.equity(wallet.amounts(),bar[3],mark[3] if mark else D(0))*fx(stamp+MINUTE)*D('.999')
        selected.append(dict(at_ms=stamp+MINUTE,equity_cny=equity))
        maximum=max(maximum,abs(wallet.spot_q*(bar[3]-f.price_at(bars,stamp+MINUTE-1))*fx(stamp+MINUTE)*D('.999')))
    return dict(status='SELECTED_PRICE_SENSITIVITY' if selected else 'SOURCE_UNAVAILABLE',
        selected_minutes=len(selected),missing_held_marks=missing,
        selected_period_drawdown=drawdown(selected) if selected else None,
        maximum_joint_valuation_difference_cny=str(maximum),original_fills_unchanged=True,
        actual_replay=False,continuous_native_mdd_verified=False,
        meaning='Only selected received spot-minute months revalue original synthetic fills. Disconnected periods are not joined; no full-window/native MDD.')


def confirmed(accounts,now):
    if {a['kind'] for a in accounts}!={'spot','coin'} or len(accounts)!=2:raise ValueError('two independent accounts required')
    for a in accounts:
        if (a['symbol']!='BTCUSDT' or a['owned'] is not True or a['protected'] is not True
                or a['pending'] is not False or type(a['receipt_ms']) is not int
                or not 0<=now-a['receipt_ms']<=60000 or r.number(a['equity_usdt'])<=0
                or r.number(a['quantity_btc'])<0):
            raise ValueError('unknown or stale independent account state')


def brake_state(state,known_closes,accounts,now):
    """Persisted hysteresis, only new known closes/current confirmed snapshots."""
    confirmed(accounts,now)
    old=dict(state or dict(high_water_cny='10000',braking=False,through_ms=-1))
    if type(now) is not int or old['through_ms']>now:raise ValueError('risk state clock reversed')
    peak=r.number(old['high_water_cny']);braking=old['braking']
    if type(braking) is not bool or peak<=0:raise ValueError('invalid persistent risk state')
    for row in known_closes:
        if row['at_ms']>now:raise ValueError('future joint high water')
        if row['at_ms']>old['through_ms']:peak=max(peak,r.number(row['equity_cny']))
    fx={r.number(a['fx']) for a in accounts}
    if len(fx)!=1:raise ValueError('joint FX clocks differ')
    value=sum((r.number(a['equity_usdt']) for a in accounts),D(0))*next(iter(fx))*D('.999')
    peak=max(peak,value);loss=1-value/peak
    if loss>=D('.10'):braking=True
    elif loss<=D('.05'):braking=False
    return dict(high_water_cny=str(peak),braking=braking,through_ms=now,drawdown=str(loss))


def brake_plan(state,account,requested=None):
    """A research plan, including requested capacity so topup cannot undo it."""
    if not state['braking'] or account['kind']!='coin':return dict(action='UNCHANGED',factor='1',orders=0)
    if account['owned'] is not True or account['protected'] is not True or account['pending'] is not False:
        return dict(action='BLOCK_UNKNOWN',orders=0)
    q=r.number(account['quantity_btc'],nonnegative=True)
    target=(q*D('.5')/D('.001')).to_integral_value(rounding='ROUND_FLOOR')*D('.001')
    return dict(action='REDUCE_CONFIRMED_COIN_RESEARCH' if q else 'HALVE_NEW_COIN_BUDGET_RESEARCH',
        factor='.5',target_btc=str(target),requested_btc=str(min(target,r.number(requested,nonnegative=True))) if requested is not None else str(target),
        held_geometry_unchanged=True,orders=0,transfers=0,native_enabled=False)


def implied_factor(iv,prior_rms,available_ms,now):
    iv,rms=map(r.number,(iv,prior_rms))
    if not 0<iv or rms<0 or type(available_ms) is not int or not 0<=now-available_ms<r.DAY:
        raise ValueError('unknown or stale implied volatility')
    return min(D(1),rms*D('365.25').sqrt()/iv)


def protection_plan(accounts,books,now):
    confirmed(accounts,now)
    for a in accounts:
        if not r.number(a['quantity_btc']):continue
        stops=a.get('confirmed_native_stops');book=books.get(a['kind'])
        if not stops or not book or type(book.get('available_ms')) is not int or not 0<=now-book['available_ms']<=5000:
            return dict(status='WAIT_NATIVE_PROTECTION_AND_DEPTH',new_risk=False,orders=0)
        quantity=abs(r.number(a['quantity_btc']));mark=r.number(a['mark_usdt'])
        valid=[s for s in stops if s.get('confirmed') is True and s.get('side')=='SELL'
               and s.get('symbol')=='BTCUSDT' and type(s.get('receipt_ms')) is int
               and 0<=now-s['receipt_ms']<=60000 and 0<r.number(s['stop_price_usdt'])<mark]
        if sum((r.number(s['quantity_btc'],nonnegative=True) for s in valid),D(0))<quantity:
            return dict(status='BLOCK_UNCOVERED_PROTECTION',new_risk=False,orders=0)
        depth=r.number(book['executable_bid_btc'],nonnegative=True)
        jump=r.number(book['confirmed_jump_fraction'],nonnegative=True)
        if depth<quantity or jump>D('.10'):
            return dict(status='BLOCK_NEW_UNCOVERED_EXECUTION_RISK',new_risk=False,orders=0)
    return dict(status='ALREADY_COVERED_BY_EXISTING_RESERVE_OR_FLAT',new_risk=True,orders=0)
