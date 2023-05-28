import asyncio
from aiogram import Bot, Dispatcher
from config import Config, load_config
from handlers import admin_handlers, user_handlers


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
    asyncio.run(main())
