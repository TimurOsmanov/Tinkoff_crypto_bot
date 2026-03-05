from aiogram import Bot, Dispatcher, Router
from aiogram.types import FSInputFile

import config


tg_api_token: str = config.telegram_api_token
bot: Bot = Bot(tg_api_token)
router_text: Router = Router()
dp: Dispatcher = Dispatcher()
dp.include_router(router_text)
# msg limit 4096 symbols


async def send_data(user_id: int, data: str) -> None:
    async with bot.session:
        await bot.send_message(user_id, f'<code>{data}</code>', parse_mode='HTML')


async def send_report_screenshot(user_id: int) -> None:
    async with bot.session:
        screen: FSInputFile = FSInputFile('save.jpg')
        await bot.send_photo(chat_id=user_id, photo=screen, request_timeout=60)
