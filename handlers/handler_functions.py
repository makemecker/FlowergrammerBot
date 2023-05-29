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
# import json


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
    # credentials_data = json.loads(google_config.credentials_json)
    credentials_data = {"type": "service_account",
                        "project_id": "cogent-task-317112",
                        "private_key_id": "b27c002652141a5b90460e1fd8c1990a0361c01e",
                        "private_key": "-----BEGIN PRIVATE "
                                       "KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCnO7EA6yCRx21N"
                                       "\niGdtZ+H2XcSRrGBRC5w9KEv6tLDyAsGg8aq3R0a3ojP2nFpsTc0xBQucuDGxZQRz\n+d6Z4eF7"
                                       "/5j1smCXcq1AlQILNhZCxOjKlItA6dCNXq45F3DIy90cEUN5IOZ1B81X"
                                       "\nJD3SWIF5hko0cl2Z8RJyWyI7OUh+8A32tfzgGNrkGabPssDeMjQaFlKH4injAVgk\nebimC604"
                                       "+68rtzImAold9w57AeIZsVdHDgFixEdRJO2xW9OsRIRtVPRBfU5lH4d0"
                                       "\nnjmF9CVKjSS5cSwYBzLPspi05meweYyqRGBAJLVwkeizTKbzcb5G8r5ehNL40KSR"
                                       "\n6x8L7XtLAgMBAAECggEAQkn8/bo2LNL6VrNtHAcDoN7GXmAPxdBuXCevBm+9fBDv"
                                       "\no9Znr0LHm17mbijIBwpH/dhcJAE3YXQDcd1oCWNqN/a3MR1GAIJqfqESMFN+O3VG"
                                       "\nOZbsJA0KqB8RvHu4Lz/wI4IMVuVdtKIlGRe6kbiXig5bN7Llu3G9uCq7xPIN9JKb"
                                       "\nTRhveJVOa8vWwX5gxwTHjOj2Nifxf9AJoJWG70JJVtRkvtcJFzEwJQpzoKz/6sku"
                                       "\nFvJRt8uID3D8ERexGDWghhjy3ECUA5zPqgvAeWlkYszhJAi1rzocJeqbUDx4UT3"
                                       "+\nVdokAu5zhM9s3vuuL0cwxBHy8Xv2ObFGL1icn7fxsQKBgQDPrDX1ZvKZM31AynT1\n0vbNI"
                                       "+Wq4tNaqG0QSBM03cIyrJn6ksErlEFSaNwZjO1ho0KppJGJ7C/Lj0FFbeYe\n4zWftHmtDCuRqd"
                                       "/YaxHLVGYh2k9CBJb8fatioFoB3p60uh1V4mF6kHo5zRyYRrtW"
                                       "\nhA369fkxlREBdKZZsgmbzGQkxQKBgQDOJls/JB4CIyMktiNXTIhC+ePqrwdxFNdR"
                                       "\nBP1VKbJODd9QpB5UysUkr1lteo8+V1IcfxrDPj1K1IEExteeW4c6sgXSBsq6Ylpl"
                                       "\ng6vSXOVnsjcHBWeFmAj2eq+htUUIbF/iT0M8b0CfHzisOXn8qZizax8f/7jXlw0k\n46Mxc"
                                       "+DAzwKBgBideOfVg/vUtovvc12P2+EE2DwhFpwwSn0bjes+Pb5z5uxkaLEZ\nqYRzGWON6LUh"
                                       "/MzOzNFkRWYDXOE13YjbtYdwhNuWDbP+RqIITtui7Vgl4C8bDCpx"
                                       "\nWtcd2o1OLdGOHdwIMTWt2k7vmOwTtjDTBjUw4pCV8qYRhYYsLCdjWpthAoGAOV2J"
                                       "\nFLf7NcMLW4LnsLpWTLT3DG5qVrhi9mO6D0HMIVZQ50LUQeovE/dLnmB1jfaEnfNs"
                                       "\nwhoGulUKFgczJxj3N4kkf35uWZFW8FrErIQ3PjTkhSqm1REqpVQcnZYwwJhP0k0W"
                                       "\nO7IFvIHWpm5UGNAk8wCDJ8dka3HYMYS6+97wExcCgYBb9IvabJ8OeNTPjN5kyiKg\ny"
                                       "/LlrQIRkCZNKe/wLUaoniJhLjbzccoAjsTE13f5WGRzx+CA2YOpknTHfFvysrtm"
                                       "\n3dsFBs4SoamUP5cznGtcB2fM2choaiPYFu652nXGr+vF12utPc9ZVeLMkcda24J7"
                                       "\nSrLNrlPf3yjGogqb+ooGAg==\n-----END PRIVATE KEY-----\n",
                        "client_email": "flowergrammerbot@cogent-task-317112.iam.gserviceaccount.com",
                        "client_id": "115563588681599898874",
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/flowergrammerbot"
                                                "%40cogent-task-317112.iam.gserviceaccount.com",
                        "universe_domain": "googleapis.com"
                        }
    credentials = service_account.Credentials.from_service_account_info(credentials_data,
                                                                        scopes=[
                                                                            'https://www.googleapis.com/auth/drive']
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
