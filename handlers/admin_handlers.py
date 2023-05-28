from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from lexicon import LEXICON
from handlers.handler_functions import IsAdmin, get_rating
from config import GoogleDrive


# Инициализируем роутер уровня модуля
router: Router = Router()


# Этот хэндлер срабатывает на команду /rating
@router.message(Command(commands='rating'), IsAdmin())
async def process_rating_command(message: Message, google_config: GoogleDrive):
    await message.answer(text=LEXICON['/rating'])
    await message.answer(text=await get_rating(google_config=google_config))


# Этот хэндлер срабатывает на команду /url
@router.message(Command(commands='url'), IsAdmin())
async def process_rating_command(message: Message, google_config: GoogleDrive):
    await message.answer(text=LEXICON['/url'] + google_config.folder_url)
