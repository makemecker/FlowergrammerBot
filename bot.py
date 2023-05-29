# -*- coding: utf-8 -*-
import logging
import asyncio
from aiogram import Bot, Dispatcher
from config import Config, load_config
from handlers import admin_handlers, user_handlers


# todo сделать отдельную ветку для разработки
# import os
# from dotenv import load_dotenv
#
# # Загрузка значений переменных окружения из файла .env
# load_dotenv()
#
# # Теперь вы можете использовать переменные окружения в вашем коде
# bot_token = os.getenv('BOT_TOKEN')
# admin_ids = os.getenv('ADMIN_IDS')
# credentials_json = os.getenv('CREDENTIALS_JSON')
# flower_folder_name = os.getenv('FLOWER_FOLDER_NAME')
# folder_url = os.getenv('FOLDER_URL')


# Функция конфигурирования и запуска бота
async def main() -> None:
    # Загружаем конфиг в переменную config
    config: Config = load_config()

    # Инициализируем бот и диспетчер
    bot: Bot = Bot(token=config.tg_bot.token)
    dp: Dispatcher = Dispatcher(google_config=config.google_drive, admins=config.tg_bot.admin_ids)

    # Регистрируем роутеры в диспетчере
    dp.include_routers(admin_handlers.router, user_handlers.router)

    # Пропускаем накопившиеся апдейты и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    # Настройка логирования
    logging.basicConfig(
        level=logging.ERROR,  # Уровень логирования (в данном случае, только ошибки)
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат записи логов
        filename='bot.log',  # Имя файла логов
    )
    # Запуск бота
    asyncio.run(main())
