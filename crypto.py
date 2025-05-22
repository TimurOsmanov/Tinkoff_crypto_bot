from bs4 import BeautifulSoup
import requests
from json import loads

from orm import CryptoTableOrm

db = CryptoTableOrm()


class Crypto:
    # keys unchangeable during the day
    storage: list = []
    today_ids: dict = {}
    today_change_rates: dict = {}
    # keys can be changeable during the day
    today_update: dict = {}
    report: str = ''

    def __init__(self, name: str, cur_prc: float = 0, change: float = 0, change_per: float = 0):
        self.name = name
        self.cur_prc = cur_prc
        self.change = change
        self.change_per = change_per
        Crypto.storage.append(self)

    def __repr__(self) -> str:
        return f'{self.name} {self.cur_prc} {self.change} {self.change_per}'

    def to_tg_msg(self) -> str:
        width: list = [3, 10, 10, 10]
        str_: str = ''
        blocks = [self.name,
                  f'{round(self.cur_prc, 2)}',
                  f'{round(self.change, 2)}',
                  f'{round(self.change_per * 100, 2)}%']
        for num, block in enumerate(blocks):
            str_ += f"{block:>{width[num]}}"
        return str_

    @classmethod
    def storage_clear(cls) -> None:
        cls.storage: list = []

    def get_coin_current_price_htx(self) -> None:
        curl = f'https://api.huobi.pro/market/trade?symbol={self.name}usdt'
        page = requests.get(curl)
        soup = BeautifulSoup(page.text, "lxml")
        soup_to_dict = loads(soup.find("p").text)
        price = soup_to_dict['tick']['data'][0]['price']
        self.cur_prc = round(price, 4)

    def get_coin_current_price_trdogr(self) -> None:
        curl = f'https://tradeogre.com/api/v1/ticker/{self.name}-USDT'
        page = requests.get(curl)
        soup = BeautifulSoup(page.text, "lxml")
        soup_to_dict = loads(soup.find("p").text)
        price = float(soup_to_dict['price'])
        self.cur_prc = round(price, 4)

    @classmethod
    def add_previous_period_sum(cls) -> None:
        data = db.select_previous_data()

        if not data:
            return

        for name, previous_price in data:
            for coin in cls.storage:
                coin: Crypto
                if coin.name == name:
                    coin.change = round(coin.cur_prc - previous_price, 4)
                    coin.change_per = round(coin.cur_prc / previous_price - 1, 4)  if previous_price != 0 else 0

    @classmethod
    def filter_assets(cls) -> None:
        cls.storage.sort(key=lambda coin: -coin.cur_prc)

    @classmethod
    def fill_today_ids(cls) -> None:
        today_ids = db.select_today_ids()

        for name, today_id in today_ids:
            cls.today_ids[name] = today_id

    @classmethod
    def fill_today_change_rates(cls) -> None:
        flag: float = 0.01
        cls.today_change_rates = {key: flag for key in cls.today_ids}

    @classmethod
    def make_first_or_last_report(cls) -> None:
        report: list = []
        for coin in cls.storage:
            coin: Crypto
            report.append(coin.to_tg_msg())
        cls.report = '\n'.join(report)

    @classmethod
    def get_crypto_current_data(cls) -> None:
        cls.storage_clear()
        coins = {'btc', 'eth', 'sol', 'jup', 'ltc', 'PYI'}

        for coin in coins:
            c = Crypto(coin)
            c.get_coin_current_price_htx() if c.name != 'PYI' else c.get_coin_current_price_trdogr()
            c.add_previous_period_sum()

        cls.filter_assets()

    @classmethod
    def insert_data_in_db(cls) -> None:
        # first operation only one time used during the day
        cls.get_crypto_current_data()

        for coin in cls.storage:
            coin: Crypto
            db.insert_data(coin)

        cls.fill_today_ids()
        cls.fill_today_change_rates()
        cls.make_first_or_last_report()

    @classmethod
    def update_sums(cls) -> None:
        # repeated operation during the day
        cls.today_update = {}
        cls.get_crypto_current_data()
        # add asset obj to list with today_id of asset in Crypto.today_ids
        for coin in cls.storage:
            coin: Crypto
            cls.today_update[coin.name] = [cls.today_ids[coin.name], coin]

        to_update = [cls.today_update[coin] for coin in cls.today_update]
        db.update_data(to_update)
        cls.make_first_or_last_report()

    @classmethod
    def check_change(cls) -> None:
        cls.get_crypto_current_data()
        report: list = []
        for coin in cls.storage:
            coin: Crypto
            if abs(coin.change_per) > cls.today_change_rates[coin.name]:
                report.append(coin.to_tg_msg())
                cls.today_change_rates[coin.name] *= 2

        if report:
            cls.report = '\n'.join(report)
