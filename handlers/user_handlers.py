from typing import List
from aiogram import Router
from aiogram.filters import Command, CommandStart, Text, and_f, or_f
from aiogram.types import Message
from lexicon import LEXICON
from handlers.handler_functions import save_to_google_drive, flower_count, predict, move_predict
from aiogram import F
from config import GoogleDrive
from aiogram import Bot
from aiogram_media_group import media_group_handler
from shutil import rmtree
from aiogram.types import Document, PhotoSize
from keyboards.kb_generator import create_inline_kb
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
import asyncio

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


# Этот хэндлер будет срабатывать на альбомы
@router.message(F.media_group_id)
@media_group_handler
async def album_handler(messages: List[Message], bot: Bot, google_config: GoogleDrive, state: FSMContext):
    data = await state.get_data()
    if data.get('dir_file_ids'):
        await data['mark_message'].delete()
        await state.clear()

    await messages[0].answer(text=LEXICON['loading'])
    username: str = messages[0].from_user.username
    all_predicts: list = []

    async def process_message(message: Message):
        content: Document | PhotoSize = message.document or message.photo[-1]
        await save_to_google_drive(username=username, content=content, content_in_group=True,
                                   bot=bot, google_config=google_config)
        all_predicts.append(await predict(content=content, bot=bot, username=username, google_config=google_config))

    await asyncio.gather(*[process_message(message) for message in messages])

    output_flower_count = await flower_count(username=username, google_config=google_config)
    if output_flower_count:
        await messages[0].answer(text=LEXICON['success'].format(output_flower_count))
        all_dir_file_ids = []

        async def process_predict(prediction):
            predict_image, predict_directory, dir_file_ids = prediction
            if len(dir_file_ids) == 1:
                await messages[0].answer(text=LEXICON['nothing'])
            else:
                await messages[0].answer_photo(photo=predict_image)
                all_dir_file_ids.append(dir_file_ids)
            rmtree(predict_directory, ignore_errors=True)

        await asyncio.gather(*[process_predict(cur_predict) for cur_predict in all_predicts])
        if len(all_dir_file_ids):
            await state.update_data(dir_file_ids=all_dir_file_ids)
            markup = create_inline_kb('good', 'bad')
            mark_message = await messages[0].answer(text=LEXICON['mark'], reply_markup=markup)
            await state.update_data(mark_message=mark_message)
    else:
        await messages[0].answer(text=LEXICON['error'])


# Этот хэндлер будет срабатывать на отправку боту фото в виде документа или просто фото
@router.message(or_f(and_f(F.document, lambda msg: msg.document.mime_type.startswith('image/')), F.photo))
async def process_doc_and_photo(message: Message, bot: Bot, google_config: GoogleDrive, state: FSMContext):
    data = await state.get_data()
    if data.get('dir_file_ids'):
        await data['mark_message'].delete()
        await state.clear()

    await message.answer(text=LEXICON['loading'])

    content: Document | PhotoSize = message.document or message.photo[-1]
    username: str = message.from_user.username

    output_flower_count = await save_to_google_drive(username=username, content=content, content_in_group=False,
                                                     bot=bot, google_config=google_config)
    if output_flower_count:
        predict_image, predict_directory, dir_file_ids = await predict(content=content, bot=bot, username=username,
                                                                       google_config=google_config)
        if len(dir_file_ids) == 1:
            await message.answer(text=LEXICON['nothing'])
            await message.answer(text=LEXICON['success'].format(output_flower_count))
        else:
            await state.update_data(dir_file_ids=dir_file_ids)

            await message.answer(text=LEXICON['success'].format(output_flower_count))
            await message.answer_photo(photo=predict_image)

            markup = create_inline_kb('good', 'bad')
            mark_message = await message.answer(text=LEXICON['mark'], reply_markup=markup)
            await state.update_data(mark_message=mark_message)
        rmtree(predict_directory, ignore_errors=True)
    else:
        await message.answer(text=LEXICON['error'])


@router.callback_query(F.data.as_('mark'))
async def process_mark(callback: CallbackQuery, mark: str, state: FSMContext, google_config: GoogleDrive):
    await callback.message.edit_text(LEXICON['loading'])
    data = (await state.get_data())['dir_file_ids']
    if isinstance(data[0], tuple):
        for preds_dir_id, file_id in data:
            await move_predict(to_dir=mark, preds_dir_id=preds_dir_id, file_id=file_id, google_config=google_config)
    else:
        for cur in data:
            for preds_dir_id, file_id in cur:
                await move_predict(to_dir=mark, preds_dir_id=preds_dir_id, file_id=file_id, google_config=google_config)
    await callback.message.edit_text(LEXICON['thanks'])
    await state.clear()
    await callback.answer()


# Этот хэндлер будет срабатывать на отправку остальных типов сообщений
@router.message()
async def process_other(message: Message, state: FSMContext):
    data = await state.get_data()
    if data.get('dir_file_ids'):
        await data['mark_message'].delete()
        await state.clear()
    await message.answer(text=LEXICON['unsupported file'])
