from AEVO.AEVO_SDK import AevoClient
from config import data
from Log.Loging import log
from eth_account import Account


def claim():
    for account1, account2 in data:
        if account1['exchange'] == 'aevo' and account2['exchange'] == 'aevo':
            aevo1 = AevoClient(account1['private_key'], Account.from_key(account1['private_key']).address,
                               account1['api_key'], account1['api_secret'], 'mainnet', account1['proxy'])
            aevo2 = AevoClient(account2['private_key'], Account.from_key(account1['private_key']).address,
                               account2['api_key'], account2['api_secret'], 'mainnet', account2['proxy'])
            for data_ in [aevo1, aevo2]:
                data_.claim_reward()


if __name__ == '__main__':
    claim()
