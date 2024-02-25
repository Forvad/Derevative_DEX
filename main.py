import random
import threading
import time
from multiprocessing.dummy import Pool

from requests import get

from AEVO.AEVO_SDK import AevoClient
from config import (coins, value, time_transaction, cycles, time_sleep, data)

from eth_account import Account
from eth_account.signers.local import LocalAccount

from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from Log.Loging import log


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


def hyper_trade(coin: str, value_: float, is_buy: bool, private_key: str, api_key: str, api_secret: str, proxy_: str):
    try:
        account: LocalAccount = Account.from_key(private_key)
        exchange_ = Exchange(account, constants.MAINNET_API_URL)
        if proxy_:
            exchange_.session.proxies = {'http': f'http://{proxy_}', 'https': f'http://{proxy_}'}

        order_result = exchange_.market_open(coin, is_buy, value_)
        if order_result["status"] == "ok":
            if is_buy:
                log().success(f'Hyper | We bought a {coin} coin in the amount of {value_}')
            else:
                log().success(f'Hyper | We sold a {coin} coin in the amount of {value_}')
        else:
            log().error(f'Hyper | error: {order_result["response"]}')
    except BaseException as error:
        log().error(error)
        time.sleep(2)
        return hyper_trade(coin, value_, is_buy, private_key, api_key, api_secret, proxy_)


def main(data_):
    exchange_buy = {'hyper': hyper_trade, 'aevo': aevo_trade}
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
            threads.append(threading.Thread(target=exchange_buy[ex['exchange']],
                                            args=(coin, values, mode, ex['private_key'], ex['api_key'],
                                                  ex['api_secret'], ex['proxy'])))

        for tr in threads:
            tr.start()

        for tr in threads:
            tr.join()

        log([i + 1, cycles]).success(f'Deals are open')

        time.sleep(random.randint(time_transaction[0], time_transaction[1]) * 60)

        for j, ex in enumerate(data_):
            if j:
                mode = is_buy
            else:
                mode = is_buy_
            exchange_buy[ex['exchange']](coin, values, mode, ex['private_key'], ex['api_key'],
                                         ex['api_secret'], ex['proxy'])

        log([i + 1, cycles]).success(f'Transactions are closed')

        time.sleep(random.randint(time_sleep[0], time_sleep[1]) * 60)


def run():
    try:
        with Pool() as pols:
            pols.map(lambda func: main(func), data)
    except threading.ThreadError as error:
        log().error(error)

if __name__ == '__main__':
    run()
