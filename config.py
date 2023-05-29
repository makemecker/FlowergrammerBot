from dataclasses import dataclass
import os


@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-боту
    admin_ids: list[int]  # Список id администраторов бота


@dataclass
class GoogleDrive:
    credentials_json: str
    flower_folder_name: str
    folder_url: str


@dataclass
class Config:
    tg_bot: TgBot
    google_drive: GoogleDrive


def load_config() -> Config:
    print("BOT_TOKEN:", os.environ.get('BOT_TOKEN'))
    print("ADMIN_IDS:", os.environ.get('ADMIN_IDS'))
    return Config(tg_bot=TgBot(token=os.environ['BOT_TOKEN'],
                               admin_ids=list(map(int, os.environ['ADMIN_IDS'].split(',')))),
                  google_drive=GoogleDrive(credentials_json=os.environ['CREDENTIALS_JSON'],
                                           flower_folder_name=os.environ['FLOWER_FOLDER_NAME'],
                                           folder_url=os.environ['FOLDER_URL']))
