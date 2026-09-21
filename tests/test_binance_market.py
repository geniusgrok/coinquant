import unittest
from pancakequant.binance import BinanceReadOnly
from pancakequant.types import Unknown


class NativeMarket(unittest.TestCase):
    def test_checkpoint_pages_without_truncation(self):
        interval=14400000;start=interval*800;end=start+241*interval;now=end+1
        reader=BinanceReadOnly(clock=lambda:now/1000);pages=[]
        def get(path,parameters=None):
            if path.endswith('/time'):return {'serverTime':now}
            pages.append(parameters)
            return [[t,'100','102','99','101','2',t+interval-1,'200',1,'1','100']
                    for t in range(parameters['startTime'],parameters['endTime']+1,interval)]
        reader.get=get;market=reader.completed_market(start=start)
        self.assertEqual(len(market['candles']),241)
        self.assertEqual([p['limit'] for p in pages],[120,120,1])
        self.assertEqual(market['candles'][0]['time'],start)
        pages.clear();self.assertEqual(reader.completed_market(start=end)['candles'],[])
        self.assertEqual(pages,[])

    def test_completed_boundary_and_missing_or_forming_candle(self):
        interval=14400000; end=interval*1000; now=end+1234
        rows=[[t,'100','102','99','101','2',t+interval-1,'200',1,'1','100']
              for t in range(end-120*interval,end,interval)]
        reader=BinanceReadOnly(clock=lambda:now/1000)
        def get(path,parameters=None):
            if path.endswith('/time'):return {'serverTime':now}
            self.assertEqual(parameters['endTime'],end-1)
            return rows
        reader.get=get
        market=reader.completed_market()
        self.assertEqual(market['complete_through'],end)
        self.assertEqual(len(market['candles']),120)
        rows[-1][0]=end
        with self.assertRaises(Unknown):reader.completed_market()
        rows.pop()
        with self.assertRaises(Unknown):reader.completed_market()
