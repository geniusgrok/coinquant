"""Deterministic native-shape venue; no credentials or network.

The real Binance snapshot/query/recovery decoders and session coordinator run on
these endpoint responses. Matching is deliberately a test fixture, not economics.
"""
from copy import deepcopy
from decimal import Decimal as D
from math import ceil
from coinquant.binance import Binance
from coinquant.campaign import Campaign
from coinquant.config import Config
from coinquant.opportunities import Opportunity
from coinquant.state import State
from coinquant.types import Unknown
from tests.test_binance_safety import rules


class Venue(Binance):
    def __init__(self, direction=1):
        self.now=1770004800000  # completed 4h boundary
        self.now=self.now//14400000*14400000+1000
        config=Config('123','/tmp/coinquant-fixture')
        super().__init__(clock=lambda:self.now/1000,authorize_writes=True)
        self.loss_fraction=config.loss_fraction;self.slip_fraction=config.slip_fraction
        self.direction=direction;self.q=D(0);self.entry=D(0);self.wallet=D(1000);self.margin=D(0)
        self.orders={};self.algos={};self.trades=[];self.calls=[];self.sent=[];self.income=[];self.margin_history=[]
        self.fraction=D(1);self.timeout_after_entry=False;self.timeout_before_entry=False
        self.reject_protection=False;self.partial_exit=False;self.fail_reads=False
        self.mark=D(100000);self.updated=self.now
        self.rules=rules();self.rules.update(status='TRADING',contractType='PERPETUAL',marginAsset='USDT')

    def wait(self,seconds):self.now+=max(1,ceil(seconds*1000)) if seconds>0 else 0
    def monotonic(self):return self.now/1000

    def dfii10_snapshot(self):
        return dict(missing_reason='fixture_absent',latest_value=None,prior20_value=None,
                    latest_value_available_ms=None,prior20_value_available_ms=None)

    def seed(self,directory):
        m=Campaign();m.last=self.now//14400000*14400000;m.model.last=m.last
        m.returns.extend([D('.02')]*20)
        m.model.active=Opportunity(m.last,self.direction,D(95000 if self.direction>0 else 105000),D(110000 if self.direction>0 else 90000),m.last+14400000)
        with State(directory,'binance:BTCUSDT:live:123') as state:state.set('linear_campaign',m.checkpoint())

    def completed_market(self,start=None,**kwargs):
        return super().completed_market(start=start,**kwargs)

    def get(self,path,parameters=None):
        p=parameters or {};self.calls.append(('GET',path,deepcopy(p)))
        if self.fail_reads:raise Unknown('fixture disconnected')
        if path.endswith('/time'):return {'serverTime':self.now}
        if path=='/api/v3/account':return {'uid':123}
        if path.endswith('/accountConfig'):return dict(dualSidePosition=False,multiAssetsMargin=False)
        if path.endswith('/symbolConfig'):return [dict(symbol='BTCUSDT',marginType='ISOLATED',leverage=20,isAutoAddMargin=False)]
        pnl=self.q*(self.mark-self.entry)
        position=dict(symbol='BTCUSDT',positionSide='BOTH',positionAmt=str(self.q),entryPrice=str(self.entry),
                      isolatedWallet=str(self.margin),updateTime=self.updated,marginAsset='USDT',markPrice=str(self.mark),
                      unRealizedProfit=str(pnl),liquidationPrice=str(self.liquidation()) if self.q else '0')
        if path=='/fapi/v3/account':
            return dict(assets=[dict(asset='USDT',walletBalance=str(self.wallet),updateTime=self.updated)],
                positions=[position],totalWalletBalance=str(self.wallet),totalUnrealizedProfit=str(pnl),
                totalMarginBalance=str(self.wallet+pnl),availableBalance=str(self.wallet-self.margin))
        if path.endswith('/positionRisk'):return [position]
        if path.endswith('/openOrders'):return [deepcopy(o) for o in self.orders.values() if o['status'] in ('NEW','PARTIALLY_FILLED')]
        if path.endswith('/openAlgoOrders'):return [deepcopy(o) for o in self.algos.values() if o['algoStatus']=='NEW']
        if path.endswith('/userTrades'):
            # Binance's default read covers the last seven days.
            default=0 if 'fromId' in p else self.now-7*86400000
            rows=[deepcopy(t) for t in self.trades if p.get('startTime',default)<=t['time']<=p.get('endTime',self.now) and t['id']>=p.get('fromId',0)]
            return rows[:p.get('limit',1000)] if 'fromId' in p or 'startTime' in p else rows[-p.get('limit',1000):]
        if path.endswith('/income'):
            return [deepcopy(r) for r in self.income if p.get('startTime',0)<=r['time']<=p.get('endTime',self.now)]
        if path.endswith('/positionMargin/history'):
            return [deepcopy(r) for r in self.margin_history if p.get('startTime',0)<=r['time']<=p.get('endTime',self.now)]
        if path.endswith('/premiumIndex'):return dict(symbol='BTCUSDT',time=self.now,markPrice=str(self.mark))
        if path.endswith('/exchangeInfo'):return {'symbols':[deepcopy(self.rules)]}
        if path.endswith('/commissionRate'):return dict(symbol='BTCUSDT',takerCommissionRate='.0005')
        if path.endswith('/leverageBracket'):return dict(symbol='BTCUSDT',brackets=[dict(notionalFloor='0',notionalCap='1000000',maintMarginRatio='.005',cum='0',initialLeverage=20)])
        if path.endswith('/depth'):return dict(E=self.now,bids=[[str(self.mark-D(1)),'100']],asks=[[str(self.mark),'100']])
        if path.endswith('/order'):
            if 'origClientOrderId' in p:
                r=self.orders.get(p['origClientOrderId'])
            else:r=next((o for o in self.orders.values() if o['orderId']==p['orderId']),None)
            if r is None:raise Unknown('fixture order unknown')
            return deepcopy(r)
        if path.endswith('/algoOrder'):
            r=self.algos.get(p['clientAlgoId'])
            if r is None:raise Unknown('fixture protection unknown')
            return deepcopy(r)
        raise AssertionError(path)

    def liquidation(self):
        return (self.q*self.entry-self.margin)/(self.q-abs(self.q)*D('.0055'))

    def pay(self,kind,amount):
        self.income.append(dict(incomeType=kind,tranId=len(self.income)+1,time=self.now,asset='USDT',
                                income=str(amount),symbol='BTCUSDT',tradeId=''))

    def fill(self,order,amount):
        self.updated=self.now
        signed=amount if order['side']=='BUY' else -amount
        price=self.mark if order['reduceOnly'] else D(order['price'])
        commission=amount*price*D('.0005')
        realized=-signed*(price-self.entry) if order['reduceOnly'] else D(0)
        if order['reduceOnly']:
            self.wallet+=realized-commission
            self.margin*=1-amount/abs(self.q)
            self.q+=signed
            if not self.q:self.entry=self.margin=D(0)
        else:
            if amount:self.entry=(abs(self.q)*self.entry+amount*price)/(abs(self.q)+amount)
            self.q+=signed;self.margin+=amount*price/20
            self.wallet-=commission
        if commission:self.pay('COMMISSION',-commission)
        if realized:self.pay('REALIZED_PNL',realized)
        if amount:
            self.trades.append(dict(symbol='BTCUSDT',positionSide='BOTH',side=order['side'],orderId=order['orderId'],id=len(self.trades)+1,time=self.now,qty=str(amount),price=str(price),commission=str(commission),commissionAsset='USDT',realizedPnl=str(realized)))
        order['executedQty']=str(D(order['executedQty'])+amount)

    def send(self,method,path,p):
        # Even the fake exchange accepts a request after the account observation,
        # so its fills cannot share the initial wallet's millisecond boundary.
        self.now += 1
        self.sent.append((method,path,deepcopy(p)));self.calls.append((method,path,deepcopy(p)))
        if path.endswith('/positionMargin'):
            self.margin+=D(p['amount']);self.updated=self.now
            self.margin_history.append(dict(symbol='BTCUSDT',asset='USDT',positionSide='BOTH',amount=p['amount'],type=1,time=self.now))
            return dict(code=200,type=1,amount=p['amount'])
        if path.endswith('/algoOrder'):
            if method=='DELETE':self.algos[p['clientAlgoId']]['algoStatus']='CANCELED';return {}
            if self.reject_protection:raise Unknown('fixture protection rejection')
            self.algos[p['clientAlgoId']]=dict(p,orderType=p['type'],algoId=len(self.algos)+1,
                closePosition=True,priceProtect=False,algoStatus='NEW',actualOrderId='0')
            return deepcopy(self.algos[p['clientAlgoId']])
        if method=='DELETE':
            self.orders[p['origClientOrderId']]['status']='CANCELED';return {}
        reduce=p.get('reduceOnly')=='true'
        if not reduce and self.timeout_before_entry:raise TimeoutError()
        quantity=D(p['quantity'])
        order=dict(p,orderId=len(self.orders)+1,clientOrderId=p['newClientOrderId'],reduceOnly=reduce,
                   origQty=p['quantity'],executedQty='0',status='FILLED')
        amount=quantity*(D('.5') if reduce and self.partial_exit else D(1) if reduce else self.fraction)
        # A fractional participation still has to land on the native lot. An
        # off-step residue cannot be closed and is not a Binance fill.
        step=D('.001')
        amount=(amount/step).to_integral_value(rounding='ROUND_FLOOR')*step
        if amount<quantity:order['status']='EXPIRED'
        self.orders[p['newClientOrderId']]=order
        self.fill(order,amount)
        if not reduce and self.timeout_after_entry:raise TimeoutError()
        return deepcopy(order)
