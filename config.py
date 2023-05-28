from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    token: str  # Токен для доступа к телеграм-боту
    admin_ids: list[int]  # Список id администраторов бота


@dataclass
class GoogleDrive:
    credentials_path: str
    flower_folder_name: str
    folder_url: str


@dataclass
class Config:
    tg_bot: TgBot
    google_drive: GoogleDrive


def load_config(path: str | None = '.env') -> Config:
    env: Env = Env()
    env.read_env(path)

    return Config(tg_bot=TgBot(token=env('BOT_TOKEN'),
                               admin_ids=list(map(int, env.list('ADMIN_IDS')))),
                  google_drive=GoogleDrive(credentials_path=env('CREDENTIALS_FILE'),
                                           flower_folder_name=env('FLOWER_FOLDER_NAME'),
                                           folder_url=env('FOLDER_URL')))
