# 'user:pass@host:port
# aevo, hyper
# если нет api_key, api_secret оставить пустыми
data = [[{'exchange': '',
          'private_key': '',
          'api_key': '',
          'api_secret': '',
          'proxy': ''},
        {'exchange': '',
         'private_key': '',
         'api_key': '',
         'api_secret': '',
         'proxy': ''}],
        ]

coins = ['SOL', "ETH", "ARB", "APT", "BTC"]

value = [200, 300]  # $, объём открываемых сделок

cycles = 5

time_transaction = [5, 10]  # минуты, время между открытием и закрытием

time_sleep = [5, 10]  # минуты, ожидание между сделками