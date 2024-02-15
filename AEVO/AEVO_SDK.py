import asyncio
import json
import random
import traceback
import ssl
import time


import requests
from eip712_structs import Address, Boolean, EIP712Struct, Uint, make_domain
from eth_account import Account
from loguru import logger
from web3 import Web3


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
        rest_headers={},
        proxy=None
    ):
        self.signing_key = signing_key
        self.wallet_address = wallet_address
        self.api_key = api_key
        self.api_secret = api_secret
        self.connection = None
        self.client = requests
        self.rest_headers = {
            "AEVO-KEY": api_key,
            "AEVO-SECRET": api_secret,
        }
        self.extra_headers = None
        self.rest_headers.update(rest_headers)

        if (env != "testnet") and (env != "mainnet"):
            raise ValueError("env must either be 'testnet' or 'mainnet'")
        self.env = env
        self.proxy = {'http': f'http://{proxy}',
                      'https': f'http://{proxy}'} if proxy else None

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
        if self.proxy:
            req = self.client.get(f"{self.rest_url}/index?asset={asset}", proxies=self.proxy)
        else:
            req = self.client.get(f"{self.rest_url}/index?asset={asset}")
        data = req.json()
        return data

    def get_markets(self, asset):
        if not self.proxy:
            req = self.client.get(f"{self.rest_url}/markets?asset={asset}")
        else:
            req = self.client.get(f"{self.rest_url}/markets?asset={asset}", proxies=self.proxy)
        data = req.json()
        return data

    def get_orderbook(self, instrument_name):
        if not self.proxy:
            req = self.client.get(
                f"{self.rest_url}/orderbook?instrument_name={instrument_name}"
            )
        else:
            req = self.client.get(
                f"{self.rest_url}/orderbook?instrument_name={instrument_name}", proxies=self.proxy
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
        if not self.proxy:
            req = self.client.post(
                f"{self.rest_url}/orders", json=data, headers=self.rest_headers
            )
        else:
            req = self.client.post(
                f"{self.rest_url}/orders", json=data, headers=self.rest_headers, proxies=self.proxy
            )
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
        if not self.proxy:
            req = self.client.post(
                f"{self.rest_url}/orders", json=data, headers=self.rest_headers
            )
        else:
            req = self.client.post(
                f"{self.rest_url}/orders", json=data, headers=self.rest_headers, proxies=self.proxy
            )
        return req.json()

    def rest_cancel_order(self, order_id):
        if not self.proxy:
            req = self.client.delete(
                f"{self.rest_url}/orders/{order_id}", headers=self.rest_headers
            )
        else:
            req = self.client.delete(
                f"{self.rest_url}/orders/{order_id}", headers=self.rest_headers, proxies=self.proxy
            )
        logger.info(req.json())
        return req.json()

    def rest_get_account(self):
        req = self.client.get(f"{self.rest_url}/account", headers=self.rest_headers)
        return req.json()

    def rest_get_apikey(self):
        if not self.proxy:
            req = self.client.get(f"{self.rest_url}/account", headers=self.rest_headers)
        else:
            req = self.client.get(f"{self.rest_url}/account", headers=self.rest_headers, proxies=self.proxy)
        data = req.json()
        api_keys = data.get('api_keys', [])
        for api_key_info in api_keys:
            return api_key_info.get('api_key')
        return None

    def rest_get_portfolio(self):
        if not self.proxy:
            req = self.client.get(f"{self.rest_url}/portfolio", headers=self.rest_headers)
        else:
            req = self.client.get(f"{self.rest_url}/portfolio", headers=self.rest_headers, proxies=self.proxy)
        return req.json()

    def rest_get_open_orders(self):
        if not self.proxy:
            req = self.client.get(
                f"{self.rest_url}/orders", json={}, headers=self.rest_headers
            )
        else:
            req = self.client.get(
                f"{self.rest_url}/orders", json={}, headers=self.rest_headers, proxies=self.proxy
            )
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
            f"{self.rest_url}/orders-all", json=body, headers=self.rest_headers
        )
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

    def sign_order(
        self, instrument_id, is_buy, limit_price, quantity, decimals=10**6
    ):
        salt = random.randint(0, 10**10)  # We just need a large enough number
        # timestamp = int(time.time())

        order_struct = Order(
            maker=self.wallet_address,  # The wallet's main address
            isBuy=is_buy,
            limitPrice=int(round(limit_price * decimals, is_buy)),
            amount=int(round(quantity * 10**6, is_buy)),
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


if __name__ == "__main__":
    pass
