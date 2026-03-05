from tinkoff.invest import Client
from tinkoff.invest.constants import INVEST_GRPC_API

import config
from orm import MainTableOrm
from report_screenshot import make_pic_from_instrument

tinkoff_api_token: str = config.tinkoff_api_token
db = MainTableOrm()


class Instrument:
    # keys unchangeable during the day
    usd: float = 0
    today_ids: dict = {}
    today_change_rates: dict = {}
    # keys can be changeable during the day
    type_sum: dict = {key: {'average': 0, 'now': 0} for key in ['all', 'currency', 'share', 'bond', 'etf', 'futures']}
    storage: dict = {key: [] for key in ['all', 'currency', 'share', 'bond', 'etf', 'futures']}
    today_update: dict = {}
    report: str = ''

    def __init__(self, asset_name: str, asset_type: str, quantity: int | float, current_price: int | float,
                 average_price: int | float, currency: str, share: float = 0,
                 previous_change: float = 0, previous_change_per: float = 0):

        self.asset_name = asset_name
        self.asset_type = asset_type
        self.quantity = quantity
        self.current_price = round(current_price, 2)
        self.average_price = round(average_price, 2) if average_price != 0 else self.current_price

        if currency == 'usd':
            self.average_price = round(self.average_price * Instrument.usd, 2)
            self.current_price = round(self.current_price * Instrument.usd, 2)

        self.current_sum = round(self.quantity * self.current_price, 2)
        self.total_change = round((self.current_price - self.average_price) * self.quantity, 2)

        self.total_change_per = round(self.current_price / self.average_price - 1, 4) \
            if self.average_price != 0 else 0

        if self.asset_name not in ['Валюта и металлы', 'Акции', 'Облигации', 'Фонды', 'Фьючерсы', 'Брокерский счет']:
            Instrument.type_sum[self.asset_type]['average'] += round(self.quantity * self.average_price, 2)
            Instrument.type_sum[self.asset_type]['now'] += round(self.quantity * self.current_price, 2)
            Instrument.type_sum['all']['average'] += round(self.quantity * self.average_price, 2)
            Instrument.type_sum['all']['now'] += round(self.quantity * self.current_price, 2)

        Instrument.storage[self.asset_type].append(self)
        self.share = share
        self.previous_change = previous_change
        self.previous_change_per = previous_change_per

    def __repr__(self) -> str:
        return (f'{self.asset_name} {self.quantity} {self.average_price} {self.current_price} {self.current_sum} '
                f'{self.total_change} {self.total_change_per} {self.share} {self.previous_change} '
                f'{self.previous_change_per}')

    def to_tg_msg(self) -> str:
        width: list = [10, 10, 10, 10, 10, 10]
        str_: str = ''
        blocks = [self.asset_name[:10],
                  round(self.current_sum, 1),
                  round(self.total_change, 1),
                  f'{round(self.total_change_per * 100, 1)}%',
                  round(self.previous_change, 1),
                  f'{round(self.previous_change_per * 100, 1)}%']
        for num, block in enumerate(blocks):
            str_ += f"{block:>{width[num]}}" if num != 0 else f"{block:<{width[num]}}"
        return str_

    @classmethod
    def storage_clear(cls) -> None:
        cls.type_sum = {key: {'average': 0, 'now': 0} for key in ['all', 'currency', 'share', 'bond', 'etf', 'futures']}
        cls.storage = {key: [] for key in ['all', 'currency', 'share', 'bond', 'etf', 'futures']}

    @classmethod
    def get_usd_quotation(cls) -> None:
        with Client(tinkoff_api_token, target=INVEST_GRPC_API) as client:
            cur_usd = client.market_data.get_last_prices(figi=['USD000UTSTOM'])
            cls.usd = cur_usd.last_prices[0].price.units + cur_usd.last_prices[0].price.nano / 10 ** 9

    @classmethod
    def add_share(cls) -> None:
        names: dict = {'currency': 'Валюта и металлы', 'share': 'Акции',
                       'bond': 'Облигации', 'etf': 'Фонды', 'futures': 'Фьючерсы', 'all': 'Брокерский счет'}
        for asset_type in cls.storage:
            for strg_asset in cls.storage[asset_type]:
                strg_asset: Instrument
                strg_asset.share = round(strg_asset.current_sum / cls.type_sum['all']['now'], 4)
            Instrument(names[asset_type], asset_type, 1,
                       # for stable correct sort
                       round(cls.type_sum[asset_type]['now'], 2) + 0.01,
                       round(cls.type_sum[asset_type]['average'], 2), None,
                       round(cls.type_sum[asset_type]['now'] / cls.type_sum['all']['now'], 4))

    @classmethod
    def add_previous_period_sum(cls) -> None:
        data = db.select_previous_data()

        if not data:
            return

        for name, previous_period_sum in data:
            if name in ['Рубли', 'Валюта и металлы']:
                # previous period change of USD include buying assets in USD
                continue
            for asset_type in cls.storage:
                for strg_asset in cls.storage[asset_type]:
                    strg_asset: Instrument
                    if strg_asset.asset_name == name:
                        strg_asset.previous_change = round(strg_asset.current_sum - previous_period_sum, 4)
                        strg_asset.previous_change_per = round(strg_asset.current_sum / previous_period_sum - 1, 4) \
                            if previous_period_sum != 0 else 0

    @classmethod
    def filter_assets(cls) -> None:
        for asset_type in cls.storage:
            cls.storage[asset_type].sort(key=lambda asset: -asset.current_sum)

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
        line1: tuple = ()
        col1: str = ''' '''
        col2: str = ''' '''
        col3: str = ''' '''
        col4: str = ''' '''
        col5: str = ''' '''
        col6: str = ''' '''
        col7: str = ''' '''
        col8: str = ''' '''
        col9: str = ''' '''
        col10: str = ''' '''
        col = {False: "lime", True: "orangered"}

        for asset_type in cls.storage:
            for strg_asset in cls.storage[asset_type]:
                strg_asset: Instrument
                if strg_asset.asset_name == 'Брокерский счет':
                    cur_sum: str = f'{strg_asset.current_sum:,.2f}'.replace(',', ' ') + '<br>'

                    if strg_asset.total_change == 0:
                        ttl_chng: str = f'{strg_asset.total_change:,.2f}'.replace(',', ' ')
                        ttl_chng_per: str = f'{round(strg_asset.total_change_per * 100, 2)}%'
                    else:
                        clr: bool = strg_asset.total_change < 0
                        t: str = f'{strg_asset.total_change:,.2f}'.replace(',', ' ')
                        t_per: str = f'{round(strg_asset.total_change_per * 100, 2)}%'
                        ttl_chng = f'<font color={col[clr]}>{t}</font><br>'
                        ttl_chng_per = f'<font color={col[clr]}>{t_per}</font><br>'

                    if strg_asset.previous_change == 0:
                        prv_chng: str = f'{strg_asset.previous_change:,.2f}'.replace(',', ' ')
                        prv_chng_per: str = f'{round(strg_asset.previous_change_per * 100, 2)}%'
                    else:
                        clr: bool = strg_asset.previous_change < 0
                        p: str = f'{strg_asset.previous_change:,.2f}'.replace(',', ' ')
                        p_per: str = f'{round(strg_asset.previous_change_per * 100, 2)}%'
                        prv_chng = f'<font color={col[clr]}>{p}</font><br>'
                        prv_chng_per = f'<font color={col[clr]}>{p_per}</font><br>'

                    line1 = (cur_sum, ttl_chng, ttl_chng_per, prv_chng, prv_chng_per)

                else:
                    col1 += strg_asset.asset_name + '<br>'
                    col2 += f'{strg_asset.quantity:,.2f}'.replace(',', ' ') + '<br>'
                    col3 += f'{strg_asset.current_price:,.2f}'.replace(',', ' ') + '<br>'
                    col4 += f'{strg_asset.average_price:,.2f}'.replace(',', ' ') + '<br>'
                    col5 += f'{strg_asset.current_sum:,.2f}'.replace(',', ' ') + '<br>'
                    col6 += f'{round(strg_asset.share * 100, 2)}%' + '<br>'

                    if strg_asset.total_change == 0:
                        col7 += f'{strg_asset.total_change:,.2f}'.replace(',', ' ') + '<br>'
                        col8 += str(strg_asset.total_change_per) + '<br>'
                    else:
                        clr: bool = strg_asset.total_change < 0
                        t: str = f'{strg_asset.total_change:,.2f}'.replace(',', ' ')
                        t_per: str = f'{round(strg_asset.total_change_per * 100, 2)}%'
                        col7 += f'<font color={col[clr]}>{t}</font><br>'
                        col8 += f'<font color={col[clr]}>{t_per}</font><br>'

                    if strg_asset.previous_change == 0:
                        col9 += f'{strg_asset.previous_change:,.2f}'.replace(',', ' ') + '<br>'
                        col10 += str(strg_asset.previous_change_per) + '<br>'
                    else:
                        clr: bool = strg_asset.previous_change < 0
                        p: str = f'{strg_asset.previous_change:,.2f}'.replace(',', ' ')
                        p_per: str = f'{round(strg_asset.previous_change_per * 100, 2)}%'
                        col9 += f'<font color={col[clr]}>{p}</font><br>'
                        col10 += f'<font color={col[clr]}>{p_per}</font><br>'

        # report screenshot will be created in current folder
        make_pic_from_instrument(line1, col1, col2, col3, col4, col5, col6, col7, col8, col9, col10)

    @classmethod
    def get_assets_current_data(cls) -> None:
        cls.storage_clear()
        with Client(tinkoff_api_token, target=INVEST_GRPC_API) as client:
            account_id = client.users.get_accounts()
            my_account_id = account_id.accounts[0].id
            # get tinkoff portfolio obj to use it variables to init Instrument objs
            assets = client.operations.get_portfolio(account_id=my_account_id).positions

            for asset in assets:
                asset_name = 'Рубли' if asset.figi == 'RUB000UTSTOM' else (
                    "USD" if asset.figi == 'USD800UTSTOM' 
                    else client.instruments.find_instrument(query=asset.figi).instruments[0].name)
                asset_type = asset.instrument_type
                quantity = asset.quantity.units + asset.quantity.nano / 10 ** 9
                nkd = asset.current_nkd.units + asset.current_nkd.nano / 10 ** 9
                current_price = asset.current_price.units + asset.current_price.nano / 10 ** 9 + nkd
                average_price = asset.average_position_price.units + asset.average_position_price.nano / 10 ** 9 + nkd
                currency = asset.average_position_price.currency
                # by init Instrument obj will be saved in Instrument.storage
                Instrument(asset_name, asset_type, quantity, current_price, average_price, currency)

        cls.add_share()
        cls.add_previous_period_sum()
        cls.filter_assets()

    @classmethod
    def insert_data_in_db(cls) -> None:
        # first operation only one time used during the day
        cls.get_usd_quotation()
        cls.get_assets_current_data()

        for asset_type in cls.storage:
            for strg_asset in cls.storage[asset_type]:
                strg_asset: Instrument
                db.insert_data(strg_asset)

        cls.fill_today_ids()
        cls.fill_today_change_rates()
        cls.make_first_or_last_report()

    @classmethod
    def update_sums(cls) -> None:
        # repeated operation during the day
        cls.today_update = {}
        cls.get_assets_current_data()
        # add asset obj to list with today_id of asset in Instrument.today_ids
        for asset_type in cls.storage:
            for strg_asset in cls.storage[asset_type]:
                strg_asset: Instrument
                cls.today_update[strg_asset.asset_name] = [cls.today_ids[strg_asset.asset_name], strg_asset]

        to_update = [cls.today_update[strg_asset] for strg_asset in cls.today_update]
        db.update_data(to_update)
        cls.make_first_or_last_report()

    @classmethod
    def check_change(cls) -> None:
        cls.get_assets_current_data()
        report: list = []
        for asset_type in cls.storage:
            for strg_asset in cls.storage[asset_type]:
                if abs(strg_asset.previous_change_per) > cls.today_change_rates[strg_asset.asset_name]:
                    strg_asset: Instrument
                    report.append(strg_asset.to_tg_msg())
                    cls.today_change_rates[strg_asset.asset_name] *= 2
        if report:
            cls.report = '\n'.join(report)
