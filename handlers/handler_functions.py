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
from ultralytics import YOLO
from aiogram.types import FSInputFile
import os


# Собственный фильтр, проверяющий юзера на админа
class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, admins: list) -> bool:
        return message.from_user.id in admins


async def get_rating(google_config: GoogleDrive):
    service = await google_api_client(google_config=google_config)
    folder_id = await get_or_create_folder(service=service, folder_name=google_config.flower_folder_name)
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
        rating_text += f"{i}. @{username}: {score} {emoji} \n\n"
    return rating_text


async def save_to_google_drive(username: str, content: Document | PhotoSize | str, content_in_group: bool,
                               bot: Bot, google_config: GoogleDrive,
                               prediction: bool = False) -> int | bool | tuple[str, str]:
    service = await google_api_client(google_config=google_config)

    save_folder_id: str = await get_username_folder_id(service=service,
                                                       flower_folder_name=google_config.flower_folder_name,
                                                       username=username)
    if prediction:
        preds_dir_id: str = await get_or_create_folder(service=service, folder_name='preds', parent_id=save_folder_id)
        save_folder_id: str = await get_or_create_folder(service=service, folder_name='other', parent_id=preds_dir_id)

    # Загружаем документ на Google Диск
    try:
        file_metadata: dict = {
            'name': os.path.split(content)[-1] if prediction else
            content.file_unique_id + '.' + (await bot.get_file(content.file_id)).file_path.rsplit('.', 1)[-1],
            'parents': [save_folder_id]
        }
        if prediction:
            if content.endswith('.txt'):
                file_bytes = content.encode('utf-8')
                mimetype = 'text/plain'
            else:
                with open(content, 'rb') as file:
                    file_bytes = file.read()
                    mimetype = 'image/' + file_metadata['name'].rsplit('.', 1)[-1]
        else:
            file = await bot.download(content.file_id)
            file_bytes = file.read()
            mimetype = 'image/' + file_metadata['name'].rsplit('.', 1)[-1]
        media_body = MediaIoBaseUpload(BytesIO(file_bytes), mimetype=mimetype, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media_body, fields='id').execute()
        file_id: str = file.get('id')

        if file_id:
            if content_in_group:
                return True
            elif prediction:
                return preds_dir_id, file_id
            return await flower_count(username, google_config)
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
        q=f"'{folder_id}' in parents and trashed=false and mimeType != 'application/vnd.google-apps.folder'",
        fields='nextPageToken, files(id)',
        pageSize=1000
    ).execute()

    file_count = len(results.get('files', []))
    return file_count


async def google_api_client(google_config: GoogleDrive):
    # Путь к файлу с учетными данными для доступа к Google Диску
    credentials_file = google_config.credentials_path

    # Аутентификация и создание клиента Google API
    credentials = service_account.Credentials.from_service_account_file(credentials_file,
                                                                        scopes=['https://www.googleapis.com/auth/drive']
                                                                        )
    return build('drive', 'v3', credentials=credentials)


async def get_username_folder_id(service: discovery.Resource, flower_folder_name: str, username: str) -> str:
    # Проверяем, существует ли папка FlowergrammerBot
    folder_id = await get_or_create_folder(service=service, folder_name=flower_folder_name)

    # Создаем папку с именем username внутри папки FlowergrammerBot
    user_folder_id = await get_or_create_folder(service, username, parent_id=folder_id)

    return user_folder_id


async def get_or_create_folder(service: discovery.Resource, folder_name: str, parent_id: str = None) -> str:
    # Поиск папки по имени и опционально родительской папке
    query = f"name='{folder_name}'"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    response = service.files().list(q=query, spaces='drive', fields='files(id)').execute()
    files = response.get('files', [])

    if files:
        return files[0]['id']
    else:
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            folder_metadata['parents'] = [parent_id]

        folder = service.files().create(body=folder_metadata, fields='id').execute()
        return folder.get('id')


async def predict(content: Document | PhotoSize, bot: Bot, username: str,
                  google_config: GoogleDrive) -> tuple[FSInputFile, str, list]:
    current_directory: str = os.getcwd()
    model: YOLO = YOLO(os.path.join(current_directory, 'yolo_weights.pt'))

    # Получение пути к файлу и его уникального идентификатора
    file_path: str = (await bot.get_file(content.file_id)).file_path
    file_unique_id = content.file_unique_id

    # Предсказание с использованием модели YOLO
    predict_directory: str = model.predict(f'https://api.telegram.org/file/bot{bot.token}/{file_path}', save=True,
                                           name=file_unique_id, save_txt=True)[0].save_dir

    file_name: str = file_path.split('/')[-1]
    predict_image_path: str = os.path.join(predict_directory, file_name)
    unique_id_image_path = os.path.join(predict_directory, file_unique_id + '.' + file_name.split('.')[-1])
    os.rename(predict_image_path, unique_id_image_path)
    predict_image: FSInputFile = FSInputFile(unique_id_image_path)
    os.remove(os.path.join(current_directory, file_name))

    labels_path = os.path.join(predict_directory, 'labels')
    txt_path = os.path.join(labels_path, file_name.split('.')[0] + '.txt')
    unique_id_txt_path = os.path.join(labels_path, file_unique_id + '.txt')
    os.rename(txt_path, unique_id_txt_path)
    dir_file_ids = []

    # Сохранение файла и получение идентификаторов файлов в Google Drive
    for file in [unique_id_image_path, unique_id_txt_path]:
        dir_file_ids.append(await save_to_google_drive(username=username, content=file, content_in_group=False, bot=bot,
                                                       google_config=google_config, prediction=True))

    return predict_image, predict_directory, dir_file_ids


async def move_predict(to_dir: str, preds_dir_id: str, file_id: str, google_config: GoogleDrive) -> None:
    service = await google_api_client(google_config=google_config)
    to_dir_id: str = await get_or_create_folder(service=service, folder_name=to_dir, parent_id=preds_dir_id)

    # Retrieve the existing parents to remove
    file = service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))

    # Move the file to the new folder
    file = service.files().update(
        fileId=file_id,
        addParents=to_dir_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()
