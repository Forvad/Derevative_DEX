import random
import threading
import time
from multiprocessing.dummy import Pool

from requests import get

from AEVO.AEVO_SDK import AevoClient
from config import (coins, value, time_transaction, cycles, time_sleep, data)
from HYPER.HYPER_SDK import HyperTrade

from eth_account import Account
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from Log.Loging import log


class Coins:
    coin: dict = dict()


def get_prices(coin_):
    """Find out the price of the coin"""
    try:
        response = get(url=f'https://api.binance.com/api/v3/ticker/price?symbol={coin_}USDT')
        check = 'binance'
        if response.status_code == 400:
            result = response.json()
            if result["msg"] == "Invalid symbol.":
                response = get(url=f'https://min-api.cryptocompare.com/data/price?fsym={coin_}&tsyms=USDT')
                check = 'cryptocompare'
        if response.status_code != 200:
            log().info('Limit on the number of requests, we sleep for 30 seconds')
            log().info(f"status_code = {response.status_code}, text = {response.text}")
            time.sleep(30)
            return get_prices(coin_)
        if check == 'binance':
            result = response.json()
            price = round(float(result['price']), 4)
        else:
            result = [response.json()]
            price = float(result[0]['USDT'])
        return price
    except BaseException as error:
        log().error(f"coin: {coin_}, error: {error}")
        time.sleep(5)
        return get_prices(coin_)


def aevo_trade(coin: str, value_: float, is_buy: bool, private_key: str, api_key: str, api_secret: str, proxy_: str):
    try:
        av = AevoClient(signing_key=private_key,
                        wallet_address=Account.from_key(private_key).address,
                        api_key=api_key,
                        api_secret=api_secret,
                        env='mainnet',
                        proxy=proxy_)

        data = av.get_markets(coin)[0]
        # balance = float(av.rest_get_account()['balance'])

        order_result = av.rest_create_market_order(data['instrument_id'], is_buy, value_)
        if order_result.get('order_id'):
            log().success(f'AEVO | We bought a {coin} coin in the amount of {value_}')
        else:
            log().success(f'AEVO | error: {order_result}')
            time.sleep(2)
            return aevo_trade(coin, value_, is_buy, private_key, api_key, api_secret, proxy_)
    except BaseException as error:
        log().error(f"AEVO | except: {error}")
        time.sleep(5)
        return aevo_trade(coin, value_, is_buy, private_key, api_key, api_secret, proxy_)


# def hyper_trade(coin: str, value_: float, is_buy: bool, private_key: str, api_key: str, api_secret: str, proxy_: str):
#     try:
#         account: LocalAccount = Account.from_key(private_key)
#         exchange_ = Exchange(account, constants.MAINNET_API_URL)
#         if proxy_:
#             exchange_.session.proxies = {'http': f'http://{proxy_}', 'https': f'http://{proxy_}'}
#
#         order_result = exchange_.market_open(coin, is_buy, value_)
#         if order_result["status"] == "ok":
#             if is_buy:
#                 log().success(f'Hyper | We bought a {coin} coin in the amount of {value_}')
#             else:
#                 log().success(f'Hyper | We sold a {coin} coin in the amount of {value_}')
#         else:
#             log().error(f'Hyper | error: {order_result["response"]}')
#     except BaseException as error:
#         log().error(error)
#         time.sleep(2)
#         return hyper_trade(coin, value_, is_buy, private_key, api_key, api_secret, proxy_)


# def drift_trade(coin: str, value_: float, is_buy: bool, private_key: str, api_key: str, api_secret: str, proxy_: str,
#                 close=None):
#     dex = DriftDex(private_key)
#     if not close:
#         if is_buy:
#             mode = 'Long'
#         else:
#             mode = 'Short'
#
#         dex.add_position(mode, value_, coin)
#     else:
#         dex.close_position(coin)


def double_hyper(coin: str, value_: float, is_buy: bool, private_key_1: str, private_key_2: str, proxy_: str):
    trade = HyperTrade(private_key_1, private_key_2, proxy_)
    open_position = trade.check_info()
    if not open_position:
        trade.open_position(coin, value_, is_buy)
        time.sleep(5)
        trade.sl_tp(coin, value_, get_prices(coin), is_buy)
        while True:
            time.sleep(30)
            if not trade.check_info():
                break
    else:
        trade.open_position(open_position[0], abs(open_position[1]), not open_position[1] > 0)
        log().info(f'Hyper | Close position | {open_position[0]} | {open_position[1]}')
        time.sleep(10)
        return double_hyper(coin, value_, is_buy, private_key_1, private_key_2, proxy_)


def double_aevo(coin: str, value_: float, is_buy: bool, private_key: str, api_key: str, api_secret: str, proxy_: str):
    address = Account.from_key(private_key).address
    av = AevoClient(signing_key=private_key,
                    wallet_address=address,
                    api_key=api_key,
                    api_secret=api_secret,
                    env='mainnet',
                    proxy=proxy_)

    volume_coin_start, _, _ = av.coin()

    positions = av.rest_get_account()['positions']
    data__ = av.get_markets(coin)[0]
    instrument_id = int(data__['instrument_id'])
    if not positions:
        order_result = av.rest_create_market_order(instrument_id, is_buy, value_)
        if order_result.get('order_id'):
            log().success(
                f'AEVO | {Account.from_key(private_key).address} | We bought a {coin} coin in the amount of {value_}')
            time.sleep(10)
            price = float(av.get_markets(coin)[0]['mark_price'])
            if is_buy:
                price_tp = price * 1.003
                price_sl = price * 0.997
            else:
                price_tp = price * 0.997
                price_sl = price * 1.003

            av.create_order_ST_LP(instrument_id, price_tp, price_sl, is_buy)
            while True:
                time.sleep(30)
                positions = av.rest_get_account().get('positions')
                if not positions:
                    break
            time.sleep(200)
            volume_coin_end, _, _ = av.coin()
            if volume_coin_end > volume_coin_start + 0.4:
                log().info(f'AEVO | {address} | The account got a boost and we sleep for 1 hour')
                time.sleep(3600)

        else:
            log().success(f'AEVO | error: {order_result}')
            time.sleep(2)
            return double_aevo(coin, value_, is_buy, private_key, api_key, api_secret, proxy_)


def trade_double(data_):
    for i in range(cycles):
        coin = random.choice(coins)
        price = get_prices(coin)
        if price > 5000:
            decimal = 3
        elif price > 1000:
            decimal = 2
        else:
            decimal = 1

        values = round(random.randint(value[0], value[1]) / price, decimal)
        is_buy = random.choice([True, False])
        is_buy_ = False if is_buy else True
        threads = []
        for j, ex in enumerate(data_):
            if not j:
                mode = is_buy
            else:
                mode = is_buy_
            if ex['exchange'] == 'aevo':
                threads.append(threading.Thread(target=double_aevo,
                                                args=(coin, values, mode, ex['private_key'], ex['api_key'],
                                                      ex['api_secret'], ex['proxy'])))
            elif ex['exchange'] == 'hyper':
                threads.append(threading.Thread(target=double_hyper,
                                                args=(coin, values, mode, ex['private_key_1'], ex['private_key_2'],
                                                      ex['proxy'])))

        for tr in threads:
            tr.start()

        for tr in threads:
            tr.join()
        if data_[0]['exchange'] == 'aevo':
            duo_address = [Account.from_key(data_[0]["private_key"]).address,
                           Account.from_key(data_[1]["private_key"]).address]
            log([i + 1, cycles]).success(f'AEVO | {duo_address[0][:5]}{duo_address[0][-5:]} and'
                                         f' {duo_address[1][:5]}{duo_address[1][-5:]} | Transactions are closed')
        else:
            duo_address = [Account.from_key(data_[0]["private_key_1"]).address,
                           Account.from_key(data_[1]["private_key_1"]).address]
            log([i + 1, cycles]).success(f'Hyper | {duo_address[0][:5]}...{duo_address[0][-5:]} and'
                                         f' {duo_address[1][:5]}...{duo_address[1][-5:]} | Transactions are closed')

        time.sleep(random.randint(time_sleep[0], time_sleep[1]) * 60)


def main(data_):
    trade_double(data_)


def run():
    try:
        with Pool(len(data)) as pols:
            pols.map(lambda func: main(func), data)
    except threading.ThreadError as error:
        log().error(error)


if __name__ == '__main__':
    run()
