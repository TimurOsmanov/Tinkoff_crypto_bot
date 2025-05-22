import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tinkoff_api import Instrument
import tg
from crypto import Crypto
import config

instrument: Instrument = Instrument
coins: Crypto = Crypto
scheduler: AsyncIOScheduler = AsyncIOScheduler()


def check_report(time_: int, class_type: str) -> None:
    if class_type == 'instrument':
        if instrument.report:
            scheduler.add_job(tg.send_data,trigger="cron", hour=time_, minute=2,
                              args=[config.telegram_user_id, instrument.report])
    else:
        if coins.report:
            scheduler.add_job(tg.send_data, trigger="cron",hour=time_, minute=5,
                              args=[config.telegram_user_id, coins.report])


async def main() -> None:
    # fiat cur
    # first action - inserting current data in db
    scheduler.add_job(instrument.insert_data_in_db, trigger="cron", hour=10)
    scheduler.add_job(tg.send_report_screenshot, trigger="cron", hour=10, minute=1, args=[config.telegram_user_id])

    # loop of checking quotes
    for hour in [11, 13, 15, 17, 19]:
        scheduler.add_job(instrument.check_change, trigger="cron", hour=hour)
        scheduler.add_job(check_report, trigger="cron", hour=hour, minute=1, args=[hour, 'instrument'])

    # last check with update today's quotes
    scheduler.add_job(instrument.update_sums, trigger="cron", hour=21)
    scheduler.add_job(tg.send_report_screenshot, trigger="cron", hour=21, minute=1, args=[config.telegram_user_id])

    # crypto cur
    # first action - inserting current data in db
    scheduler.add_job(coins.insert_data_in_db, trigger="cron", hour=10, minute=3)
    scheduler.add_job(check_report, trigger="cron", hour=10, minute=4, args=[10, 'coins'])

    # loop of checking quotes
    for hour in [11, 13, 15, 17, 19]:
        scheduler.add_job(coins.check_change, trigger="cron", hour=hour, minute=3)
        scheduler.add_job(check_report, trigger="cron", hour=hour, minute=4, args=[hour, 'coins'])

    # last check with update today's quotes
    scheduler.add_job(coins.update_sums, trigger="cron", hour=21, minute=3)
    scheduler.add_job(check_report, trigger="cron", hour=21, minute=4, args=[21, 'coins'])

    scheduler.start()

    while True:
        await asyncio.sleep(1)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
