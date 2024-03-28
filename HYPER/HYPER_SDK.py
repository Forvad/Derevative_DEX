import time

from eth_account import Account
from eth_account.signers.local import LocalAccount
from hyperliquid.exchange import Exchange
from hyperliquid.info import Info
from hyperliquid.utils import constants

from Log.Loging import log


class HyperTrade:
    def __init__(self, private_key_1, private_key_2, proxy_: str):
        self.private_key_1 = private_key_1
        self.private_key_2 = private_key_2
        self.address = Account.from_key(self.private_key_1).address
        self.exchange_ = Exchange(Account.from_key(self.private_key_2), constants.MAINNET_API_URL)
        if proxy_:
            self.exchange_.session.proxies = {'http': f'http://{proxy_}', 'https': f'http://{proxy_}'}

    def open_position(self, coin: str, value_: float, is_buy: bool, ):
        try:
            order_result = self.exchange_.market_open(coin, is_buy, value_)
            if order_result["status"] == "ok":
                if is_buy:
                    log().success(f'Hyper | {self.address} | We bought a {coin} coin in the amount of {value_}')
                else:
                    log().success(f'Hyper | {self.address} | We sold a {coin} coin in the amount of {value_}')
            else:
                log().error(f'Hyper | error: {order_result["response"]}')
        except BaseException as error:
            log().error(error)
            time.sleep(2)
            return self.open_position(coin, value_, is_buy)

    def check_info(self):
        account: LocalAccount = Account.from_key(self.private_key_1)
        exchange_ = Exchange(account, constants.MAINNET_API_URL)
        info = Info(constants.MAINNET_API_URL, True)
        open_orders = info.user_state(exchange_.wallet.address)['assetPositions']
        if open_orders:
            for position in open_orders:
                position = position['position']
                return [position["coin"], float(position["szi"])]
        else:
            return []

    def sl_tp(self, coin: str, value: (int, float), price: (int, float), is_buy: bool):
        if price > 100:
            decimal = 1
        elif price > 1:
            decimal = 2
        else:
            decimal = 3
        if is_buy:
            price_tp = round(price * 1.003, decimal)
            price_sl = round(price * 0.997, decimal)
        else:
            price_tp = round(price * 0.997, decimal)
            price_sl = round(price * 1.003, decimal)
        all_price = [price_sl, price_tp]
        stop_order_type = {"trigger": {"triggerPx": price_sl, "isMarket": True, "tpsl": "sl"}}
        tp_order_type = {"trigger": {"triggerPx": price_tp, "isMarket": True, "tpsl": "tp"}}
        for i, data_ in enumerate([stop_order_type, tp_order_type]):
            self.exchange_.order(coin, not is_buy, value, all_price[i], data_, reduce_only=True)
            time.sleep(3)

    def chek_balance(self):
        account: LocalAccount = Account.from_key(self.private_key_1)
        exchange_ = Exchange(account, constants.MAINNET_API_URL)
        info = Info(constants.MAINNET_API_URL, True)
        open_orders = info.user_state(exchange_.wallet.address)
        print(open_orders)


if __name__ == '__main__':
    pass

