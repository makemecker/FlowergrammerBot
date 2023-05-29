from config import GoogleDrive
from aiogram.types import Document, PhotoSize
from googleapiclient.discovery import build
from google.oauth2 import service_account
from aiogram import Bot
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError
from io import BytesIO
from googleapiclient import discovery
from aiogram.filters import BaseFilter
from aiogram.types import Message
import json


# Собственный фильтр, проверяющий юзера на админа
class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, admins: list) -> bool:
        return message.from_user.id in admins


async def get_rating(google_config: GoogleDrive):
    service = await google_api_client(google_config=google_config)
    folder_id = await get_folder_id(service=service, folder_name=google_config.flower_folder_name)
    query = f"'{folder_id}' in parents and mimeType = 'application/vnd.google-apps.folder'"
    response = service.files().list(q=query).execute()

    input_folders = {}
    if 'files' in response:
        for file in response['files']:
            input_folders[file['name']] = file['id']

    rating = {}
    for folder_name in input_folders:
        rating[folder_name] = await count_files_in_folder(service, input_folders[folder_name])

    sorted_rating = sorted(rating.items(), key=lambda item: item[1], reverse=True)
    rating_text = ''
    for i, (username, score) in enumerate(sorted_rating, start=1):
        if i == 1:
            emoji = '✅'  # Зеленая галочка для первой записи
        else:
            emoji = ''
        rating_text += f"{i}. {username}: {score} {emoji} \n\n"
    return rating_text


async def save_to_google_drive(username: str, content: Document | PhotoSize, bot: Bot, google_config: GoogleDrive):
    service = await google_api_client(google_config=google_config)

    user_folder_id = await get_username_folder_id(service=service,
                                                  flower_folder_name=google_config.flower_folder_name,
                                                  username=username)

    content_data = {
        'name': '',
        'mime_type': ''
    }
    if isinstance(content, Document):
        content_data['name'] = content.file_name
        content_data['mime_type'] = content.mime_type
    else:
        content_data['name'] = (await bot.get_file(content.file_id)).file_path.rsplit('/', 1)[-1]
        content_data['mime_type'] = 'image/' + content_data['name'].rsplit('.', 1)[-1]
    # Загружаем документ на Google Диск
    try:
        file_metadata = {
            'name': content_data['name'],
            'parents': [user_folder_id]
        }
        input_file = await bot.download(content.file_id)
        file_bytes = input_file.read()
        media_body = MediaIoBaseUpload(BytesIO(file_bytes), mimetype=content_data['mime_type'], resumable=True)
        file = service.files().create(body=file_metadata, media_body=media_body, fields='id').execute()
        file_id = file.get('id')

        if file_id:
            return await flower_count(username=username, google_config=google_config)
        else:
            return False

    except HttpError:
        return False


async def flower_count(username: str, google_config: GoogleDrive) -> int:
    service = await google_api_client(google_config=google_config)
    user_folder_id = await get_username_folder_id(service=service,
                                                  flower_folder_name=google_config.flower_folder_name,
                                                  username=username)
    file_count = await count_files_in_folder(service, user_folder_id)
    return file_count


async def count_files_in_folder(service: discovery.Resource, folder_id: str):
    # Код для подсчета количества файлов в папке
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields='nextPageToken, files(id)',
        pageSize=1000
    ).execute()

    file_count = len(results.get('files', []))
    return file_count


async def google_api_client(google_config: GoogleDrive):
    # Путь к файлу с учетными данными для доступа к Google Диску
    credentials_data = json.loads(google_config.credentials_json)

    # Аутентификация и создание клиента Google API
    credentials = service_account.Credentials.from_service_account_info(credentials_data,
                                                                        scopes=['https://www.googleapis.com/auth/drive']
                                                                        )
    return build('drive', 'v3', credentials=credentials)


async def get_username_folder_id(service: discovery.Resource, flower_folder_name: str, username: str) -> str:
    # Проверяем, существует ли папка FlowergrammerBot
    folder_id = await get_folder_id(service=service, folder_name=flower_folder_name)
    if folder_id is None:
        folder_id = await create_folder(service, folder_name=flower_folder_name)

    # Создаем папку с именем username внутри папки FlowergrammerBot
    user_folder_id = await get_folder_id(service, username, parent_id=folder_id)
    if user_folder_id is None:
        user_folder_id = await create_folder(service, username, parent_id=folder_id)

    return user_folder_id


async def get_folder_id(service: discovery.Resource, folder_name: str, parent_id: str = None):
    # Поиск папки по имени и опционально родительской папке
    query = f"name='{folder_name}'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    files = response.get('files', [])
    if files:
        return files[0]['id']
    else:
        return None


async def create_folder(service: discovery.Resource, folder_name: str, parent_id: str = None):
    # Создание новой папки с указанным именем и опционально родительской папкой
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    if parent_id:
        folder_metadata['parents'] = [parent_id]

    folder = service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')
