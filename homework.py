import os
import time
import logging

import requests
import telegram

from dotenv import load_dotenv


load_dotenv()

PRAKTIKUM_TOKEN = os.getenv("PRAKTIKUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
YP_URL = "https://praktikum.yandex.ru/api/user_api/homework_statuses/"
ERRORS_LIMIT = 20
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
    try:
        homework_statuses = requests.get(YP_URL, params=params, headers=headers)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error in connection with Yandex url: {e}")
    else:
        return homework_statuses.json()


def parse_homework_status(homework):
    hw_name = homework.get("homework_name")
    hw_status = homework.get("status")
    if hw_status:
        if hw_status == "rejected":
            verdict = 'К сожалению в работе нашлись ошибки.'
        elif hw_status == "reviewing":
            verdict = 'Работу взяли в работу. Проверка еще не завершилась.'
        else:
            verdict = ('Ревьюеру всё понравилось, можно приступать '
                       'к следующему уроку.')
        return f'У вас проверили работу "{hw_name}"!\n\n{verdict}'


def send_message(message, bot_client):
    logger.info("sending message to Telegram-chat")
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    logger.debug("Telegram-bot initializated")
    current_timestamp = int(time.time())
    errors_counter = 0
    old_hw_status = None
    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get("homeworks"):
                new_hw_status = new_homework.get("homeworks")[0]["status"]
                if new_hw_status != old_hw_status:
                    send_message(parse_homework_status(
                                 new_homework.get("homeworks")[0]), bot_client)
                    errors_counter = 0
                    old_hw_status = new_hw_status
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
