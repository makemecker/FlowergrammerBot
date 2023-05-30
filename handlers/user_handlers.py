from aiogram import Router
from aiogram.filters import Command, CommandStart, Text, and_f, or_f
from aiogram.types import Message
from lexicon import LEXICON
from handlers.handler_functions import save_to_google_drive, flower_count
from aiogram import F
from config import GoogleDrive
from aiogram import Bot

# Инициализируем роутер уровня модуля
router: Router = Router()


# Этот хэндлер срабатывает на команду /start
@router.message(CommandStart())
async def process_start_command(message: Message):
    await message.answer(text=LEXICON['/start'])


# Этот хэндлер срабатывает на команду /help
@router.message(Command(commands='help'))
async def process_help_command(message: Message):
    await message.answer(text=LEXICON['/help'])


# Этот хэндлер срабатывает на команду /contacts
@router.message(Command(commands='contacts'))
async def process_help_command(message: Message):
    await message.answer(text=LEXICON['/contacts'])


# Этот хэндлер будет срабатывать на отправку текста
@router.message(~Text(startswith='/'), F.text)
async def process_doc(message: Message):
    await message.answer(text=LEXICON['text'])


# Этот хэндлер срабатывает на отсутствие username
@router.message(~F.from_user.username)
async def process_no_username(message: Message):
    await message.answer(text=LEXICON['no username'])


# Этот хэндлер срабатывает на команду /size
@router.message(Command(commands='size'))
async def process_size_command(message: Message, google_config: GoogleDrive):
    await message.answer(text=LEXICON['loading'])
    output_flower_count = await flower_count(username=message.from_user.username,
                                             google_config=google_config)
    await message.answer(text=LEXICON['/size'].format(str(output_flower_count)))


# Этот хэндлер будет срабатывать на отправку боту фото в виде документа или просто фото
@router.message(or_f(and_f(F.document, lambda msg: msg.document.mime_type.startswith('image/')), F.photo))
async def process_doc(message: Message, bot: Bot, google_config: GoogleDrive):
    await message.answer(text=LEXICON['loading'])
    content = message.document if message.document else message.photo[-1]
    output_flower_count = await save_to_google_drive(username=message.from_user.username,
                                                     content=content, bot=bot,
                                                     google_config=google_config)
    if output_flower_count:
        await message.answer(text=LEXICON['success'].format(str(output_flower_count)))
    else:
        await message.answer(text=LEXICON['error'])


# Этот хэндлер будет срабатывать на отправку остальных типов сообщений
@router.message()
async def process_other(message: Message):
    await message.answer(text=LEXICON['unsupported file'])
