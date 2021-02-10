import os
import time
import logging
import json

import requests
import telegram

from dotenv import load_dotenv


load_dotenv()

PRAKTIKUM_TOKEN = os.environ["PRAKTIKUM_TOKEN"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
PRAKTIKUM_HOMEWORK_URL = (
    "https://praktikum.yandex.ru/api/user_api/homework_statuses/")
ERRORS_LIMIT = 10
bot_client = telegram.Bot(token=TELEGRAM_TOKEN)


class TelegramBotHandler(logging.Handler):
    def __init__(self, tg_bot, chat_id):
        super().__init__()
        self.chat_id = chat_id
        self.tg_bot = tg_bot

    def emit(self, record):
        log_entry = self.format(record)
        self.tg_bot.send_message(chat_id=self.chat_id, text=log_entry)


logging.basicConfig(
    level='DEBUG',
    filename='homework.log',
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
)
logger = logging.getLogger(__name__)
error_handler = TelegramBotHandler(bot_client, CHAT_ID)
error_handler.setLevel(logging.ERROR)
logger.addHandler(error_handler)


def get_homework_statuses(current_timestamp=None):
    headers = {
        "Authorization": f"OAuth {PRAKTIKUM_TOKEN}",
    }
    params = {
        "from_date": current_timestamp,
    }
    homework_statuses = {}
    try:
        homework_statuses = requests.get(
            PRAKTIKUM_HOMEWORK_URL,
            params=params,
            headers=headers
        ).json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logger.error(f"Error in connection with Yandex url: {e}")
    return homework_statuses


def parse_homework_status(homework):
    hw_name = homework.get("homework_name", "имя не задано")
    hw_status = homework.get("status")
    homework_statuses = {
        "rejected": "К сожалению в работе нашлись ошибки.",
        "reviewing": "Работу взяли в работу. Проверка еще не завершилась.",
        "approved": ("Ревьюеру всё понравилось, можно приступать "
                     "к следующему уроку."),
    }
    verdict = homework_statuses.get(hw_status, "unknown status")
    return f'У вас проверили работу "{hw_name}"!\n\n{verdict}'


def send_message(message, bot_client):
    logger.info("sending message to Telegram-chat")
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    logger.debug("Telegram-bot initializated")
    current_timestamp = int(time.time())
    errors_counter = 0
    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get("homeworks"):
                send_message(parse_homework_status(
                             new_homework.get("homeworks")[0]), bot_client)
                errors_counter = 0
            current_timestamp = new_homework.get("current_date",
                                                 current_timestamp)
            time.sleep(1200)
        except Exception as e:
            errors_counter += 1
            logger.error(f"Error: {e}")
            time.sleep(3)
            if errors_counter > ERRORS_LIMIT:
                logger.error("Error's limit exceeded. Time-out for set time")
                time.sleep(3600)


if __name__ == '__main__':
    main()
