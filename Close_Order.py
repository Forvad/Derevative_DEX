import time

from AEVO.AEVO_SDK import AevoClient
from config import data
from Log.Loging import log
from eth_account import Account
from requests.exceptions import ProxyError
from urllib3.exceptions import MaxRetryError


def check_balance():
    answer = input("Закрывать сделки y/n:")
    for account1, account2 in data:
        if account1['exchange'] == 'aevo' and account2['exchange'] == 'aevo':
            aevo1 = AevoClient(account1['private_key'], Account.from_key(account1['private_key']).address,
                               account1['api_key'], account1['api_secret'], 'mainnet', account1['proxy'])
            aevo2 = AevoClient(account2['private_key'], Account.from_key(account1['private_key']).address,
                               account2['api_key'], account2['api_secret'], 'mainnet', account2['proxy'])
            for data_ in [aevo1, aevo2]:
                balance = data_.rest_get_account()
                position = balance.get('positions')
                if position:
                    position = position[0]
                    log().info(f'address: {balance.get("account")} | symbol: {position.get("asset")} |'
                               f' value: {position.get("amount")} | position:'
                               f' {"Long" if position.get("asset") == "buy" else "Short"}')
                    if answer == "y":
                        if position['side'] == 'buy':
                            is_buy = False
                        else:
                            is_buy = True
                        order_result = data_.rest_create_market_order(position['instrument_id'], is_buy,
                                                                     float(position['amount']))
                        if not order_result.get('order_id'):
                            log().success(f'AEVO | error: {order_result}')
                            time.sleep(2)
                        time.sleep(2)
                        position_ = data_.rest_get_account().get('positions')
                        if not position_:
                            log().success(f'Close position | {position.get("asset")} | {position.get("amount")}')
        time.sleep(1)


    else:
        log().success('Открытых позиции нет')


if __name__ == '__main__':
    check_balance()
