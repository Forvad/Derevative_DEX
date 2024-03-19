from AEVO.AEVO_SDK import AevoClient
from config import data
from Log.Loging import log


def check_balance():
    for account1, account2 in data:
        aevo1 = AevoClient(account1['private_key'], account1['address'], account1['api_key'], account1['api_secret'],
                           'mainnet', account1['proxy'])
        aevo2 = AevoClient(account2['private_key'], account2['address'], account2['api_key'], account2['api_secret'],
                           'mainnet', account2['proxy'])
        for data_ in [aevo1, aevo2]:
            balance = data_.rest_get_account()
            token, value = data_.coin()
            log().info(f'address: {balance.get("account")} | balance: {balance.get("balance")} |'
                       f' token: {token} | value: {value}')


if __name__ == '__main__':
    check_balance()

