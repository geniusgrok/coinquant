# coding: UTF-8
import json
import queue
import threading
import time
import traceback
from datetime import datetime

import requests
import websocket
from pytz import UTC

from src import logger, notify, to_data_frame
from src.config import config as conf
from src.exchange.binance_futures.binance_futures_api import Client


PUBLIC_SOCKET = "public"
MARKET_SOCKET = "market"
PRIVATE_SOCKET = "private"

MAINNET = "mainnet"
TESTNET = "testnet"

SOCKET_ROOTS = {
    MAINNET: "wss://fstream.binance.com",
    TESTNET: "wss://stream.binancefuture.com",
}

PRIVATE_EVENTS = (
    "ORDER_TRADE_UPDATE",
    "ACCOUNT_UPDATE",
    "ALGO_UPDATE",
)

WS_PING_INTERVAL = 90
WS_PING_TIMEOUT = 10


def generate_nonce():
    return int(round(time.time() * 1000))


def get_listenkey(api_key, api_secret, testnet):
    client = Client(api_key=api_key, api_secret=api_secret, testnet=testnet)
    listen_key = client.stream_get_listen_key()
    return listen_key


class BinanceFuturesWs:

    def __init__(self, account, pair, bin_size, test=False):
        """
        constructor
        """
        self.account = account
        self.pair = pair.lower()
        self.bin_size = bin_size
        self.testnet = test
        self.use_healthcecks = True
        self.last_heartbeat = 0
        self.is_running = True
        self.handlers = {}
        self.listenKey = None
        self.event_queue = queue.Queue()
        self.dispatch_thread = None

        self.api_key = conf['binance_test_keys'][self.account]['API_KEY'] \
            if self.testnet else conf['binance_keys'][self.account]['API_KEY']
        self.api_secret = conf['binance_test_keys'][self.account]['SECRET_KEY'] \
            if self.testnet else conf['binance_keys'][self.account]['SECRET_KEY']

        self.socket_root = SOCKET_ROOTS[TESTNET if self.testnet else MAINNET]
        self.sockets = {
            PUBLIC_SOCKET: None,
            MARKET_SOCKET: None,
            PRIVATE_SOCKET: None,
        }
        self.socket_threads = {
            PUBLIC_SOCKET: None,
            MARKET_SOCKET: None,
            PRIVATE_SOCKET: None,
        }
        self.socket_apps = {}
        self._socket_lock = threading.Lock()

        self.__start_dispatcher()
        self.__get_auth_user_data_streams()
        self.__start_all_sockets()
        self.__keep_alive_user_datastream(self.listenKey)

    def __public_streams(self):
        return [f"{self.pair}@bookTicker"]

    def __market_streams(self):
        streams = [f"{self.pair}@ticker"]
        streams.extend(f"{self.pair}@kline_{timeframe}" for timeframe in self.bin_size)
        return streams

    def __private_events(self):
        return list(PRIVATE_EVENTS)

    def __get_wss_endpoint(self, channel):
        if channel == PUBLIC_SOCKET:
            streams = "/".join(self.__public_streams())
            return f"{self.socket_root}/public/stream?streams={streams}"

        if channel == MARKET_SOCKET:
            streams = "/".join(self.__market_streams())
            return f"{self.socket_root}/market/stream?streams={streams}"

        if channel == PRIVATE_SOCKET:
            if not self.listenKey:
                return None
            events = "/".join(self.__private_events())
            return f"{self.socket_root}/private/ws?listenKey={self.listenKey}&events={events}"

        raise ValueError(f"Unknown websocket channel: {channel}")

    def __get_auth_user_data_streams(self):
        """
        authenticate user data streams
        """
        if len(self.api_key) > 0 and len(self.api_secret):
            self.listenKey = get_listenkey(self.api_key, self.api_secret, testnet=self.testnet)
        else:
            logger.info("WebSocket is not able to get listenKey for user data streams")

    def __create_socket_app(self, channel):
        endpoint = self.__get_wss_endpoint(channel)
        if endpoint is None:
            return None

        return websocket.WebSocketApp(
            endpoint,
            on_message=lambda ws, message: self.__on_message(channel, ws, message),
            on_error=lambda ws, exception: self.__on_error(channel, ws, exception),
            on_close=lambda ws, status_code, status_message: self.__on_close(
                channel, ws, status_code, status_message
            ),
        )

    def __run_socket(self, channel):
        app = self.socket_apps.get(channel)
        if app is not None:
            app.run_forever(
                ping_interval=WS_PING_INTERVAL,
                ping_timeout=WS_PING_TIMEOUT,
            )

    def __start_socket(self, channel):
        app = self.__create_socket_app(channel)
        if app is None:
            return

        with self._socket_lock:
            self.socket_apps[channel] = app
            self.sockets[channel] = app

        thread = threading.Thread(target=self.__run_socket, args=(channel,))
        thread.daemon = True
        thread.start()

        with self._socket_lock:
            self.socket_threads[channel] = thread

    def __start_all_sockets(self):
        for channel in (PUBLIC_SOCKET, MARKET_SOCKET, PRIVATE_SOCKET):
            self.__start_socket(channel)

    def __start_dispatcher(self):
        self.dispatch_thread = threading.Thread(target=self.__dispatch_loop)
        self.dispatch_thread.daemon = True
        self.dispatch_thread.start()

    def __dispatch_loop(self):
        while True:
            item = self.event_queue.get()
            if item is None:
                self.event_queue.task_done()
                break

            key, action, value = item
            try:
                self.__emit_now(key, action, value)
            finally:
                self.event_queue.task_done()

    def __restart_socket(self, channel):
        if not self.is_running:
            return

        logger.info(f"Websocket On Close: Restart {channel}")
        notify(f"Websocket On Close: Restart {channel}")
        time.sleep(1)
        self.__start_socket(channel)

    def __close_socket(self, channel):
        app = self.socket_apps.get(channel)
        if app is not None:
            app.close()

    def __restart_private_socket(self):
        self.__close_socket(PRIVATE_SOCKET)

    def __keep_alive_user_datastream(self, listenKey):
        """
        keep alive user data stream, needs to ping every 60m
        """
        def loop_function():
            while self.is_running:
                try:
                    listen_key = get_listenkey(self.api_key, self.api_secret, self.testnet)

                    if self.listenKey != listen_key:
                        logger.info("listenKey Changed!")
                        notify("listenKey Changed!")
                        self.listenKey = listen_key
                        self.__restart_private_socket()

                    if self.use_healthcecks:
                        try:
                            requests.get(conf['healthchecks.io'][self.account]['listenkey_heartbeat'])
                        except Exception as e:
                            logger.error(f"Listen Key Health Check Error - {str(e)}")
                            pass

                    time.sleep(600)
                except Exception as e:
                    logger.error(f"Keep Alive Error - {str(e)}")
                    notify(f"Keep Alive Error - {str(e)}")

        timer = threading.Timer(10, loop_function)
        timer.daemon = True
        if listenKey is not None:
            timer.start()
        else:
            self.__get_auth_user_data_streams()
            timer.start()

    def __on_error(self, channel, ws, exception):
        """
        On Error listener
        :param ws:
        :param message:
        """
        is_expected_disconnect = exception.__class__.__name__ == "WebSocketConnectionClosedException"
        if is_expected_disconnect:
            logger.warning(f"{channel} websocket disconnected: {exception}")
            notify(f"{channel} websocket disconnected: {exception}")
            return

        logger.error(f"{channel} websocket error: {exception}")
        logger.error(traceback.format_exc())

        notify(f"Error occurred on {channel} websocket. {exception}")
        notify(traceback.format_exc())

    def __normalize_payload(self, message):
        obj = json.loads(message)
        payload = obj.get('data', obj)
        return obj, payload

    def __on_message(self, channel, ws, message):
        """
        On Message listener
        :param ws:
        :param message:
        :return:
        """
        try:
            _, datas = self.__normalize_payload(message)

            if 'e' not in datas:
                return

            e = datas['e']
            action = ""

            if e.startswith("kline"):
                if self.use_healthcecks:
                    current_minute = datetime.now().time().minute
                    if self.last_heartbeat != current_minute:
                        try:
                            requests.get(conf['healthchecks.io'][self.account]['websocket_heartbeat'])
                            self.last_heartbeat = current_minute
                        except Exception:
                            pass

                data = [{
                    "timestamp": datas['k']['T'],
                    "high": float(datas['k']['h']),
                    "low": float(datas['k']['l']),
                    "open": float(datas['k']['o']),
                    "close": float(datas['k']['c']),
                    "volume": float(datas['k']['v']),
                }]
                data[0]['timestamp'] = datetime.fromtimestamp(data[0]['timestamp'] / 1000).astimezone(UTC)
                self.__emit(datas['k']['i'], datas['k']['i'], to_data_frame([data[0]]))
            elif e.startswith("24hrTicker"):
                self.__emit('instrument', action, datas)
            elif e.startswith("ACCOUNT_UPDATE"):
                self.__emit('position', action, datas['a']['P'])
                # This bot currently only consumes the primary USDT balance entry.
                self.__emit('wallet', action, datas['a']['B'][0])
                self.__emit('margin', action, datas['a']['B'][0])
            elif e.startswith("ORDER_TRADE_UPDATE"):
                self.__emit('order', action, datas['o'])
            elif e.startswith("ALGO_UPDATE"):
                algo_data = datas['o'].copy()
                algo_data['c'] = algo_data.get('caid', '')
                algo_data['i'] = str(algo_data.get('aid', '0'))
                algo_data['z'] = algo_data.get('aq', '0')
                algo_data['sp'] = algo_data.get('tp', '0')
                algo_data['ap'] = algo_data.get('ap', '0.0')
                self.__emit('order', action, algo_data)
            elif e.startswith("listenKeyExpired"):
                # Binance documents this separately from transport disconnect, but we
                # force a reconnect here as a defensive fail-safe to restore user data.
                self.__emit('close', action, datas)
                self.__get_auth_user_data_streams()
                logger.info("listenKeyExpired!!!")
                self.__restart_private_socket()
            elif e.startswith("bookTicker"):
                self.__emit('bookticker', action, datas)

        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc())

    def __emit(self, key, action, value):
        self.event_queue.put((key, action, value))

    def __emit_now(self, key, action, value):
        """
        send data
        """
        if key in self.handlers:
            self.handlers[key](action, value)

    def __on_close(self, channel, ws, status_code, status_message):
        """
        On Close Listener
        :param ws:
        """
        with self._socket_lock:
            if self.socket_apps.get(channel) is ws:
                self.socket_apps[channel] = None
                self.sockets[channel] = None
                self.socket_threads[channel] = None

        if 'close' in self.handlers:
            self.handlers['close']()

        if self.is_running:
            self.__restart_socket(channel)

    def on_close(self, func):
        """
        on close fn
        :param func:
        """
        self.handlers['close'] = func

    def bind(self, key, func):
        """
        bind fn
        :param key:
        :param func:
        """
        self.handlers[key] = func

    def close(self):
        """
        close websocket
        """
        self.is_running = False
        self.event_queue.put(None)
        for channel in (PUBLIC_SOCKET, MARKET_SOCKET, PRIVATE_SOCKET):
            self.__close_socket(channel)
