"""Margin transfer outcomes and native write classification (no network)."""
import json
import tempfile
import unittest
from decimal import Decimal as D
from email.message import Message
from io import BytesIO
from urllib.error import HTTPError

from coinquant.binance import Binance
from coinquant.binance_safety import add_margin, send_once
from coinquant.state import State
from coinquant.types import Blocked, Unknown
from tests.test_binance_safety import Native, rules


class History(Native):
    def __init__(self):
        super().__init__();self.history=[];self.fail_snapshot=False
    def snapshot(self,uid):
        if self.fail_snapshot:raise Unknown('fixture read outage')
        return super().snapshot(uid)
    def get(self,path,parameters=None):
        assert path=='/fapi/v1/positionMargin/history',path
        p=parameters
        return [r for r in self.history if p['startTime']<=r['time']<=p['endTime']]
    def send(self,method,path,p):
        answer=super().send(method,path,p)
        if path=='/fapi/v1/positionMargin':
            self.history.append(dict(symbol='BTCUSDT',type=1,deltaType='USER_ADJUST',amount=p['amount'],
                                     asset='USDT',positionSide='BOTH',time=int(self.clock()*1000)))
        return answer


class MarginIntentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.state=State(self.tmp.name,'binance:BTCUSDT:live:123').__enter__();self.native=History()
    def tearDown(self):self.state.__exit__();self.tmp.cleanup()
    def add(self,send=None,target='40'):
        return add_margin(self.native,self.state,send or self.native.send,'123',100,target,
                          instrument=rules(),authorized=True)
    def intents(self):
        return self.state.db.execute("SELECT status,result FROM intents WHERE kind='binance_margin'").fetchall()

    def test_amount_is_rounded_up_to_native_settlement_precision(self):
        self.add(target='30.123456789123')
        self.assertEqual(self.native.sent[0][2]['amount'],'0.12345679')
        self.assertGreaterEqual(D(self.native.margin),D('30.123456789123'))

    def test_acknowledged_transfer_survives_a_failed_readback(self):
        def send(*args):
            answer=self.native.send(*args);self.native.fail_snapshot=True;return answer
        with self.assertRaises(Unknown):self.add(send)
        self.assertEqual(self.state.pending(),[])
        self.assertEqual(self.intents()[0][0],'confirmed')
        self.native.fail_snapshot=False
        self.assertEqual(self.native.recover_pending(self.state),{'resolved':0,'pending':0})

    def test_lost_answer_is_settled_from_margin_history_only(self):
        def send(*args):self.native.send(*args);raise TimeoutError()
        with self.assertRaises(Unknown):self.add(send)
        self.assertEqual(len(self.state.pending()),1)
        self.assertEqual(self.native.recover_pending(self.state)['resolved'],1)
        self.assertEqual(self.intents()[0][0],'confirmed')
        self.assertEqual(len(self.native.sent),1)

    def test_ambiguous_history_stays_unknown(self):
        def send(*args):self.native.send(*args);raise TimeoutError()
        with self.assertRaises(Unknown):self.add(send)
        self.native.history.append(dict(self.native.history[0],amount='3'))
        self.assertEqual(self.native.recover_pending(self.state)['pending'],1)

    def test_absent_transfer_is_terminal_only_after_a_complete_late_window(self):
        def send(*args):raise TimeoutError()
        with self.assertRaises(Unknown):self.add(send)
        self.assertEqual(self.native.recover_pending(self.state)['pending'],1)
        start=self.native.clock();self.native.clock=lambda:start+601
        self.assertEqual(self.native.recover_pending(self.state)['pending'],0)
        self.assertEqual(self.intents()[0][0],'rejected')


class HTTP:
    def __init__(self,answer):self.answer=answer;self.calls=0
    def open(self,request,timeout):
        self.calls+=1
        if isinstance(self.answer,Exception):raise self.answer
        return BytesIO(self.answer)


def rejection(status,code):
    body=json.dumps(dict(code=code,msg='fixture')).encode()
    return HTTPError('https://fapi.binance.com/fapi/v1/order',status,'fixture',Message(),BytesIO(body))


class WriteClassificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.state=State(self.tmp.name,'binance:BTCUSDT:live:123').__enter__()
        self.payload=dict(symbol='BTCUSDT',positionSide='BOTH',side='BUY',type='LIMIT',timeInForce='IOC',
                          quantity='.001',price='100000',newClientOrderId='cq-x')
    def tearDown(self):self.state.__exit__();self.tmp.cleanup()
    def reader(self,answer):
        http=HTTP(answer)
        return Binance(key='k',secret='s',opener=http,authorize_writes=True),http
    def attempt(self,reader):
        self.state.prepare('cq-x','binance_order',self.payload)
        send_once(self.state,'cq-x',reader.send,'POST','/fapi/v1/order',self.payload)
        return self.state.db.execute("SELECT status,result FROM intents WHERE id='cq-x'").fetchone()

    def test_expired_deadline_is_recorded_as_never_sent(self):
        reader,http=self.reader(b'{}');reader.deadline=reader.monotonic()-1
        status,result=self.attempt(reader)
        self.assertEqual((status,http.calls),('rejected',0))
        self.assertIn('not_sent',json.loads(result))

    def test_documented_native_rejection_is_terminal(self):
        reader,http=self.reader(rejection(400,-2019))
        self.assertEqual(self.attempt(reader)[0],'rejected')

    def test_unknown_execution_codes_and_server_errors_stay_pending(self):
        for answer in (rejection(400,-1007),rejection(503,-1001),rejection(400,-1006),TimeoutError()):
            self.state.db.execute("DELETE FROM intents");self.state.db.commit()
            reader,_http=self.reader(answer)
            self.assertEqual(self.attempt(reader)[0],'unknown',answer)

    def test_numeric_margin_amount_is_parsed_exactly(self):
        reader,_http=self.reader(b'{"amount":623.19382938882948900,"code":200,"type":1}')
        answer=reader.send('POST','/fapi/v1/positionMargin',dict(symbol='BTCUSDT',positionSide='BOTH',
                                                                  amount='623.193829388829489',type=1))
        self.assertEqual(answer['amount'],D('623.19382938882948900'))

    def test_read_rejections_remain_unknown(self):
        reader,_http=self.reader(rejection(400,-2013))
        with self.assertRaises(Unknown) as caught:reader.get('/fapi/v1/order',{'symbol':'BTCUSDT','origClientOrderId':'cq-x'})
        self.assertEqual(type(caught.exception),Unknown)

    def test_margin_rejection_blocks_without_pending(self):
        native=Native()
        def refuse(*args):raise Blocked('fixture local refusal')
        with self.assertRaises(Blocked):
            add_margin(native,self.state,refuse,'123',100,'40',instrument=rules(),authorized=True)
        self.assertEqual(self.state.pending(),[])
