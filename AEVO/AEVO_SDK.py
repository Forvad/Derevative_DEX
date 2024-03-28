import random
import traceback
import time

from requests import Session
from eip712_structs import Address, Boolean, EIP712Struct, Uint, make_domain, String
from eth_account import Account
from loguru import logger
from web3 import Web3
from Log.Loging import log


w3 = Web3(
    Web3.HTTPProvider("http://127.0.0.1:8545")
)  # This URL doesn"t actually do anything, we just need a web3 instance

CONFIG = {
    "testnet": {
        "rest_url": "https://api-testnet.aevo.xyz",
        "ws_url": "wss://ws-testnet.aevo.xyz",
        "signing_domain": {
            "name": "Aevo Testnet",
            "version": "1",
            "chainId": "11155111",
        },
    },
    "mainnet": {
        "rest_url": "https://api.aevo.xyz",
        "ws_url": "wss://ws.aevo.xyz",
        "signing_domain": {
            "name": "Aevo Mainnet",
            "version": "1",
            "chainId": "1",
        },
    },
}

# timestamp = int(time.time())


class Order(EIP712Struct):
    maker = Address()
    isBuy = Boolean()
    limitPrice = Uint(256)
    amount = Uint(256)
    salt = Uint(256)
    instrument = Uint(256)
    timestamp = Uint(256)


class AevoClient:
    def __init__(
        self,
        signing_key="",
        wallet_address="",
        api_key="",
        api_secret="",
        env="testnet",
        proxy=None
    ):
        self.signing_key = signing_key
        self.wallet_address = wallet_address
        self.api_key = api_key
        self.api_secret = api_secret
        self.connection = None
        self.client = Session()
        self.client.headers = {
            "AEVO-KEY": api_key,
            "AEVO-SECRET": api_secret,
        }
        self.extra_headers = None

        if (env != "testnet") and (env != "mainnet"):
            raise ValueError("env must either be 'testnet' or 'mainnet'")
        self.env = env
        if proxy:
            self.client.proxies = {'http': f'http://{proxy}',
                                   'https': f'http://{proxy}'}

    @property
    def address(self):
        return w3.eth.account.from_key(self.signing_key).address

    @property
    def rest_url(self):
        return CONFIG[self.env]["rest_url"]

    @property
    def ws_url(self):
        return CONFIG[self.env]["ws_url"]

    @property
    def signing_domain(self):
        return CONFIG[self.env]["signing_domain"]

    async def close_connection(self):
        try:
            logger.info("Closing connection...")
            await self.connection.close()
            logger.info("Connection closed")
        except Exception as e:
            logger.error("Error thrown when closing connection")
            logger.error(e)
            logger.error(traceback.format_exc())

    # Public REST API
    def get_index(self, asset):
        req = self.client.get(f"{self.rest_url}/index?asset={asset}")
        data = req.json()
        return data

    def get_markets(self, asset):
        req = self.client.get(f"{self.rest_url}/markets?asset={asset}")
        data = req.json()
        return data

    def get_orderbook(self, instrument_name):
        req = self.client.get(
            f"{self.rest_url}/orderbook?instrument_name={instrument_name}"
        )
        data = req.json()
        return data

    # Private REST API
    def rest_create_order(
        self, instrument_id, is_buy, limit_price, quantity, post_only=True
    ):
        data = self.create_order_rest_json(
            int(instrument_id), is_buy, limit_price, quantity, post_only
        )
        req = self.client.post(
            f"{self.rest_url}/orders", json=data)
        return req.json()

    def rest_create_market_order(self, instrument_id, is_buy, quantity):
        limit_price = 0
        if is_buy:
            limit_price = 2**256 - 1

        data = self.create_order_rest_json(
            int(instrument_id),
            is_buy,
            limit_price,
            quantity,
            decimals=1,
            post_only=False,
        )
        req = self.client.post(
            f"{self.rest_url}/orders", json=data)
        return req.json()

    def rest_cancel_order(self, order_id):
        req = self.client.delete(
            f"{self.rest_url}/orders/{order_id}")
        logger.info(req.json())
        return req.json()

    def rest_get_account(self) -> dict:
        req = self.client.get(f"{self.rest_url}/account")
        return req.json()

    def rest_get_apikey(self):
        req = self.client.get(f"{self.rest_url}/account")
        data = req.json()
        api_keys = data.get('api_keys', [])
        for api_key_info in api_keys:
            return api_key_info.get('api_key')
        return None

    def rest_get_portfolio(self):
        req = self.client.get(f"{self.rest_url}/portfolio")
        return req.json()

    def rest_get_open_orders(self):
        req = self.client.get(
            f"{self.rest_url}/orders", json={})
        return req.json()

    def rest_cancel_all_orders(
        self,
        instrument_type=None,
        asset=None,
    ):
        body = {}
        if instrument_type:
            body["instrument_type"] = instrument_type

        if asset:
            body["asset"] = asset

        req = self.client.delete(
            f"{self.rest_url}/orders-all", json=body)
        return req.json()

    # Private WS Commands
    def create_order_ws_json(
        self,
        instrument_id,
        is_buy,
        limit_price,
        quantity,
        post_only=True,
        # timestamp=int(time.time()),
    ):
        salt, signature = self.sign_order(instrument_id, is_buy, limit_price, quantity)
        return {
            "instrument": instrument_id,
            "maker": self.wallet_address,
            "is_buy": is_buy,
            "amount": str(int(round(quantity * 10**6, is_buy))),
            "limit_price": str(int(round(limit_price * 10**6, is_buy))),
            "salt": str(salt),
            "signature": signature,
            "post_only": post_only,
            "timestamp": int(time.time()),
        }

    def create_order_rest_json(
        self,
        instrument_id,
        is_buy,
        limit_price,
        quantity,
        post_only=True,
        decimals=10**6,
        # timestamp=int(time.time()),
    ):
        salt, signature = self.sign_order(
            instrument_id, is_buy, limit_price, quantity, decimals=decimals
        )
        return {
            "maker": self.wallet_address,
            "is_buy": is_buy,
            "instrument": instrument_id,
            "limit_price": str(int(round(limit_price * decimals, is_buy))),
            "amount": str(int(round(quantity * 10**6, is_buy))),
            "salt": str(salt),
            "signature": signature,
            "post_only": post_only,
            "timestamp": int(time.time()),
        }

    def create_order_ST_LP(
            self,
            instrument_id: int,
            price_TP: (int, float),
            price_SL: (int, float),
            is_buy_: bool
        ):
        print_ = False
        is_buy = True if not is_buy_ else False
        decimals = 10 ** 6
        if is_buy_:
            limit_price = 0
        else:
            limit_price = 115792089237316195423570985008687907853269984665640564039457584007913129639935
        data = [['TAKE_PROFIT', price_TP], ['STOP_LOSS', price_SL]]
        for i in data:
            while True:
                salt, signature = self.sign_order(
                    instrument_id, is_buy, limit_price, 0, decimals=decimals
                )
                if isinstance(i[1], tuple):
                    i[1] = i[1][0]
                triger = str(int(i[1] * 10 ** 6))
                json_data = {
                    'maker': self.address,
                    'is_buy': is_buy,
                    'instrument': instrument_id,
                    'limit_price': str(limit_price),
                    'amount': '0',
                    'salt': salt,
                    'stop': i[0],
                    'trigger': triger,
                    'signature': signature,
                    'reduce_only': True,
                    'timestamp': str(int(time.time())),
                    'close_position': True,
                }
                r = self.client.post('https://api.aevo.xyz/orders', json=json_data).json()
                if not r.get('order_id'):
                    log().error(f'Error open order {i[0]} | {r}')
                    print_ = True
                    time.sleep(1)
                else:
                    if print_:
                        log().success('Order open not error ^_^')
                    time.sleep(1)
                    break

    def rest_create_order_stop(
        self, instrument_id, is_buy, limit_price, quantity, post_only=True
    ):
        data = self.create_order_rest_json(
            int(instrument_id), is_buy, limit_price, quantity, post_only
        )
        req = self.client.post(
            f"{self.rest_url}/orders", json=data)
        return req.json()

    def sign_order(
            self, instrument_id, is_buy, limit_price, quantity, decimals=10 ** 6
    ):
        salt = random.randint(0, 10 ** 10)  # We just need a large enough number
        # timestamp = int(time.time())

        order_struct = Order(
            maker=self.wallet_address,  # The wallet's main address
            isBuy=is_buy,
            limitPrice=int(round(limit_price * decimals, is_buy)) if limit_price < 1_000_000 else int(limit_price),
            amount=int(round(quantity * 10 ** 6, is_buy)),
            salt=salt,
            instrument=instrument_id,
            timestamp=int(time.time()),  # Add the timestamp to the order object
        )

        domain = make_domain(**self.signing_domain)
        signable_bytes = Web3.keccak(order_struct.signable_bytes(domain=domain))
        return (
            salt,
            Account._sign_hash(signable_bytes, self.signing_key).signature.hex(),
        )

    def sign_transaction(
        self, decimals=10**6
    ):
        salt = random.randint(0, 10**10)  # We just need a large enough number
        # timestamp = int(time.time())

        transaction_struct = Order(
            maker=self.wallet_address,  # The wallet's main address
            salt=salt,
            timestamp=int(time.time()),  # Add the timestamp to the order object
        )

        domain = make_domain(**self.signing_domain)
        signable_bytes = Web3.keccak(transaction_struct.signable_bytes(domain=domain))
        return (
            salt,
            Account._sign_hash(signable_bytes, self.signing_key).signature.hex(),
        )

    def coin(self):

        response = self.client.get('https://api.aevo.xyz/farm-boost').json()
        token = round(float(response.get('curr_epoch_aevo_earned', 0)), 1)
        token_ = int(float(response.get("prev_epoch_aevo_earned", 0)))
        value = int(float(response.get('boosted_volume', 0)) / float(response.get('farm_boost_avg', 0)))
        return token, value, token_

    def claim_reward(self):
        statistic = float(self.client.get("https://api.aevo.xyz/referral-statistics").json()
                          .get("total_referee_discount_unclaimed", 0))
        re = self.client.post("https://api.aevo.xyz/claim-referral-rewards").json()
        if re.get("success"):
            log().success(f"{self.address} | clame refferal reward | {statistic}$")
        else:
            log().error(f"{self.address} | error: {re}")


if __name__ == "__main__":
    pass
