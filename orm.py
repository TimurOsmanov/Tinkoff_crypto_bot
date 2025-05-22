import os
import datetime
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import select
from sqlalchemy.sql import func

engine = create_engine('sqlite:///tinkoff.db')
session_factory = sessionmaker(engine)
metadata = MetaData()


class Base(DeclarativeBase):
    pass


class MainTableOrm(Base):
    __tablename__ = 'main_table'
    asset_id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    asset_name: Mapped[str]
    asset_type: Mapped[str]
    quantity: Mapped[int]
    current_price: Mapped[float]
    average_price: Mapped[float]
    current_sum: Mapped[float]
    share: Mapped[float]
    total_change: Mapped[float]
    total_change_per: Mapped[float]
    previous_change: Mapped[float]
    previous_change_per: Mapped[float]

    @staticmethod
    def select_previous_data():
        with session_factory() as session:
            # create list of date pairs (starts with today and yesterday)
            past_ten_days = [((datetime.datetime.now() - datetime.timedelta(days=x)).strftime("%Y-%m-%d"),
                              (datetime.datetime.now() - datetime.timedelta(days=x + 1)).strftime("%Y-%m-%d"))
                             for x in range(10)]

            for today, yesterday in past_ten_days:
                query = select(MainTableOrm.asset_name, MainTableOrm.current_sum,
                               ).filter(MainTableOrm.date.between(yesterday, today))
                result = session.execute(query)
                data = result.all()
                session.commit()
                if data:
                    return data

    @staticmethod
    def select_today_ids():
        with session_factory() as session:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            query = select(MainTableOrm.asset_name, MainTableOrm.asset_id
                           ).filter(MainTableOrm.date.between(today, tomorrow))
            result = session.execute(query)
            data = result.all()
            session.commit()

            return data

    @staticmethod
    def insert_data(asset):
        with session_factory() as session:
            data = MainTableOrm(asset_name=asset.asset_name, asset_type=asset.asset_type,
                                quantity=asset.quantity, average_price=asset.average_price,
                                current_price=asset.current_price, current_sum=asset.current_sum,
                                share=asset.share, total_change=asset.total_change,
                                total_change_per=asset.total_change_per,
                                previous_change=asset.previous_change,
                                previous_change_per=asset.previous_change_per)
            session.add(data)
            session.commit()

    @staticmethod
    def update_data(update_: list):
        with session_factory() as session:
            for line in update_:
                today_id, asset_updated = line
                asset = session.get(MainTableOrm, today_id)
                asset.current_price = asset_updated.current_price
                asset.current_sum = asset_updated.current_sum
                asset.share = asset_updated.share
                asset.total_change = asset_updated.total_change
                asset.total_change_per = asset_updated.total_change_per
                asset.previous_change = asset_updated.previous_change
                asset.previous_change_per = asset_updated.previous_change_per
                session.commit()


class CryptoTableOrm(Base):
    __tablename__ = 'crypto'
    asset_id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    name: Mapped[str]
    cur_prc: Mapped[float]
    change: Mapped[float]
    change_per: Mapped[float]

    @staticmethod
    def select_previous_data():
        with session_factory() as session:
            # create list of date pairs (starts with today and yesterday)
            past_ten_days = [((datetime.datetime.now() - datetime.timedelta(days=x)).strftime("%Y-%m-%d"),
                              (datetime.datetime.now() - datetime.timedelta(days=x + 1)).strftime("%Y-%m-%d"))
                             for x in range(10)]

            for today, yesterday in past_ten_days:
                query = select(CryptoTableOrm.name, CryptoTableOrm.cur_prc,
                               ).filter(CryptoTableOrm.date.between(yesterday, today))
                result = session.execute(query)
                data = result.all()
                session.commit()
                if data:
                    return data

    @staticmethod
    def select_today_ids():
        with session_factory() as session:
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            query = select(CryptoTableOrm.name, CryptoTableOrm.asset_id
                           ).filter(CryptoTableOrm.date.between(today, tomorrow))
            result = session.execute(query)
            data = result.all()
            session.commit()
            return data

    @staticmethod
    def insert_data(coin):
        with session_factory() as session:
            data = CryptoTableOrm(name=coin.name, cur_prc=coin.cur_prc, change=coin.change, change_per=coin.change_per)
            session.add(data)
            session.commit()

    @staticmethod
    def update_data(update_: list):
        with session_factory() as session:
            for line in update_:
                today_id, coin_updated = line
                coin = session.get(CryptoTableOrm, today_id)
                coin.cur_prc = coin_updated.cur_prc
                coin.change = coin_updated.change
                coin.change_per = coin_updated.change_per
                session.commit()


def create_main_table():
    Base.metadata.create_all(engine)


if os.path.exists("tinkoff.db"):
    # tables = inspect(engine).get_table_names()  # 2 check created tables
    print('tinkoff.db exists')
    print('main_table has already been created')
    print('crypto has already been created')
else:
    create_main_table()
