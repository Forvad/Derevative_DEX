import time

from AEVO.AEVO_SDK import AevoClient
from config import data
from Log.Loging import log


def check_balance():
    open_position = []
    for account1, account2 in data:
        aevo1 = AevoClient(account1['private_key'], account1['address'], account1['api_key'], account1['api_secret'],
                           'mainnet', account1['proxy'])
        aevo2 = AevoClient(account2['private_key'], account2['address'], account2['api_key'], account2['api_secret'],
                           'mainnet', account2['proxy'])
        for data_ in [aevo1, aevo2]:
            balance = data_.rest_get_account()
            position = balance.get('positions')
            if position:
                position = position[0]
                open_position.append([data_, position])
                log().info(f'address: {balance.get("account")} | symbol: {position.get("asset")} |'
                           f' value: {position.get("amount")} | position:'
                           f' {"Long" if position.get("asset") == "buy" else "Short"}')
    time.sleep(1)
    if open_position:
        answer = input('Закрыть все сделки y/n: ')
        if answer == 'y':
            for aevo, position in open_position:
                if position['side'] == 'buy':
                    is_buy = False
                else:
                    is_buy = True
                aevo.rest_create_market_order(position['instrument_id'], is_buy, float(position['amount']))
                time.sleep(2)
                position_ = aevo.rest_get_account().get('positions')
                if not position_:
                    log().success(f'Close position | {position.get("asset")} | {position.get("amount")}')

    else:
        log().success('Открытых позиции нет')


if __name__ == '__main__':
    check_balance()
