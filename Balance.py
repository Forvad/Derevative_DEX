from AEVO.AEVO_SDK import AevoClient
from config import data
from Log.Loging import log
from eth_account import Account


def check_balance():
    avg_token = 0
    balance_all = 0
    token_all = 0
    for account1, account2 in data:
        if account1['exchange'] == 'aevo' and account2['exchange'] == 'aevo':
            aevo1 = AevoClient(account1['private_key'], Account.from_key(account1['private_key']).address,
                               account1['api_key'], account1['api_secret'], 'mainnet', account1['proxy'])
            aevo2 = AevoClient(account2['private_key'], Account.from_key(account1['private_key']).address,
                               account2['api_key'], account2['api_secret'], 'mainnet', account2['proxy'])
            for data_ in [aevo1, aevo2]:
                balance = data_.rest_get_account()
                token, value, token_ = data_.coin()
                avg_token += token_
                token_all += token
                balance_all += float(balance.get("balance", 0))
                log().info(f'address: {balance.get("account")} | balance: {balance.get("balance")} |'
                           f' token: {token} | token_epoch: {token_} | value: {value}')
    log().success(f"1 epoch token all: {avg_token} | token_farm: {token_all} | all balance: {balance_all}$")


if __name__ == '__main__':
    check_balance()

