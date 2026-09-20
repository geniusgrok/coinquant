# coding: UTF-8
import os
import random

import math
import re
import time

import numpy
from hyperopt import hp

from src import logger, notify
from src.indicators import (highest, lowest, med_price, avg_price, typ_price, 
                            atr, MAX, sma, bbands, macd, adx, sar, sarext, 
                            cci, rsi, crossover, crossunder, last, rci, 
                            double_ema, ema, triple_ema, wma, ssma, hull, 
                            supertrend, rsx, donchian)
from src.exchange.bitmex.bitmex import BitMex
from src.exchange.binance_futures.binance_futures import BinanceFutures
from src.exchange.bitmex.bitmex_stub import BitMexStub
from src.exchange.binance_futures.binance_futures_stub import BinanceFuturesStub
from src.bot import Bot

# Debug strategy
# python3 main.py --account binanceaccount1 --exchange binance --pair WLDUSDT --strategy Debug 2>&1 | tee -a logs/binance/Debug.log

class ChaserTester(Bot):

    leverage = 1

    #set automatically later
    quote_rounding = 2 # USDT Rounding
    asset_rounding = 3 # ETH BTC Rounding

    balance = 0
    started = False
    finished = False

    def __init__(self): 
        # set time frame here       
        Bot.__init__(self, ['4h'])

    def entry_position_size(self, balance, price):
        position_size = balance*self.leverage/price
        return round(position_size, self.asset_rounding)
    
    def options(self):
        return {}

    def strategy(self, action, open, close, high, low, volume):

        self.exchange.leverage = self.leverage
        self.asset_rounding = self.exchange.asset_rounding
        self.quote_rounding = self.exchange.quote_rounding

        self.balance = self.exchange.get_balance()
        position_size = self.exchange.get_position_size()

        logger.info(f"---------------------")   
        
        # get lot or set your own value which will be used to size orders 
        # careful default lot is about 20x your account size !!!
        logger.info(f"Time:      {self.exchange.timestamp}")
        logger.info(f"Balance:   {self.balance}")
        # logger.info(f"Margin:    {self.exchange.get_margin()}")
        logger.info(f"Position:  {position_size}")
        # logger.info(f"Lot:       {self.exchange.get_lot()}")
        logger.info(f"Leverage:  {self.exchange.get_leverage()}")
        #logger.info(f"Account:   {self.exchange.get_account_information()}")

        logger.info(f"---------------------")   

        long = True     
        post_only = True
        

        ticker=self.exchange.get_orderbook_ticker()
        price=float(ticker["bidPrice"] if long else ticker["askPrice"])

        # we need to test 4 types of orders
        #
        # 1. Market order - limit=0 and stop=0 - Done 2026-04-28 11:35AM
        # 2. Limit order - limit=price and stop=0
        # 3. Stop Market Order - limit=0 and stop=trigger_price
        # 4. Stop Limit Order - limit=price and stop=trigger_price
        #
        # Also need to test where stop is rejected as it will trigger immediated
        # and Limit at current price to test post only error handling

        MARKET = "MARKET"
        LIMIT = "LIMIT"
        STOP_MARKET = "STOP_MAKRET"
        STOP_LIMIT = "STOP_LIMIT"

        #***********
        # Change this to test various order types with chaser
        #***********
        test_chaser = MARKET

        stop = 0
        limit = 0

        if test_chaser == MARKET:
            stop=0
            limit=0
        elif test_chaser == LIMIT:
            stop=0
            limit = price
        elif test_chaser == STOP_MARKET:
            stop = round(price + self.exchange.tick_size*5, self.quote_rounding) #to avoid rounding errors
            limit=0
        elif test_chaser == STOP_LIMIT:
            stop = round(price + self.exchange.tick_size*5, self.quote_rounding) #to avoid rounding errors
            limit = round(price + self.exchange.tick_size*4, self.quote_rounding) #to avoid rounding errors

        def entry_callback(order):
            logger.info(order)
            if(order['status'] == "FILLED"):
                self.exchange.order("Close", not long, self.exchange.get_position_size(), stop=0, limit=0, post_only=post_only, reduce_only=True, callback=lambda order: logger.info(order), chaser=True)
                self.finished = True
        
        if position_size == 0 and not self.started:
            self.started = True
            self.exchange.order("Long", long, self.entry_position_size(self.balance, close[-1]), stop=stop, limit=limit, post_only=post_only, callback=entry_callback, chaser=True)            
