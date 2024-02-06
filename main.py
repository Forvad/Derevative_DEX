import random
import threading
import time

from requests import get

from AEVO.AEVO_SDK import AevoClient
from config import (private_key1, coins, value, time_transaction, cycles, exchange, time_sleep, data)

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


def hyper_trade(coin: str, value_: float, is_buy: bool, private_key: str, api_key: str, api_secret: str, proxy_: str):
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


def main():
    exchange_buy = {'hyper': hyper_trade, 'aevo': aevo_trade}
    for i in range(cycles):
        coin = random.choice(coins)
        values = round(random.randint(value[0], value[1]) / get_prices(coin), 2)
        is_buy = random.choice([True, False])
        is_buy_ = False if is_buy else True
        threads = []
        for ex1, ex2 in data:
            threads.append(threading.Thread(target=exchange_buy[ex1['exchange']],
                                            args=(coin, values, is_buy, ex1['private_key'], ex1['api_key'],
                                                  ex1['api_secret'], ex1['proxy'])))
            threads.append(threading.Thread(target=exchange_buy[ex2['exchange']],
                                            args=(coin, values, is_buy_, ex2['private_key'], ex2['api_key'],
                                                  ex2['api_secret'], ex2['proxy'])))

        for tr in threads:
            tr.start()

        for tr in threads:
            tr.join()

        log([i + 1, cycles]).success(f'Deals are open')

        time.sleep(random.randint(time_transaction[0], time_transaction[1]) * 60)

        threads = []

        for ex1, ex2 in data:
            threads.append(threading.Thread(target=exchange_buy[ex1['exchange']],
                                            args=(coin, values, is_buy_, ex1['private_key'], ex1['api_key'],
                                                  ex1['api_secret'], ex1['proxy'])))
            threads.append(threading.Thread(target=exchange_buy[ex2['exchange']],
                                            args=(coin, values, is_buy, ex2['private_key'], ex2['api_key'],
                                                  ex2['api_secret'], ex2['proxy'])))

        for tr in threads:
            tr.start()

        for tr in threads:
            tr.join()

        log([i + 1, cycles]).success(f'Transactions are closed')

        time.sleep(random.randint(time_sleep[0], time_sleep[1]) * 60)


def test():
    coin = random.choice(coins)
    # values = round(random.randint(value[0], value[1]) / get_prices(coin), 2)
    values = 0.01
    log().info(values)
    is_buy_ = False
    aevo_trade(coin, values, is_buy_, private_key1, api_key1, apy_secret1, proxy[0])


def test2():
    coin = 'BNB'
    # coin = random.choice(coins)
    # values = round(random.randint(value[0], value[1]) / get_prices(coin), 2)
    values = 0.08
    log().info(values)
    is_buy_ = True
    hyper_trade(coin, values, is_buy_, private_key2, api_key2, apy_secret2, proxy[1])

if __name__ == '__main__':
    main()
