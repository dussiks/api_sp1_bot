import os
import time
import logging

import requests
import telegram
from dotenv import load_dotenv


load_dotenv()

logging.basicConfig(
    level='DEBUG',
    filename='api.log',
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(name)s, %(message)s',
)
logger = logging.getLogger(__name__)

PRAKTIKUM_TOKEN = os.getenv("PRAKTIKUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
YP_URL = "https://praktikum.yandex.ru/api/user_api/homework_statuses"
ERRORS_TEXT = "Error's limit exceeded. Time-out for pointed duration"
ERRORS_LIMIT = 3


def get_homework_statuses(current_timestamp=None):
    headers = {
        "Authorization": f"OAuth {PRAKTIKUM_TOKEN}",
    }
    params = {
        "from_date": current_timestamp,
    }
    try:
        homework_statuses = requests.get(YP_URL, params=params, headers=headers)
    except requests.exceptions.RequestException as error:
        logger.error(error, exc_info=True)
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
            verdict = 'Ревьюеру всё понравилось, можно приступать к следующему уроку.'
        return f'У вас проверили работу "{hw_name}"!\n\n{verdict}'


def send_message(message, bot_client):
    return bot_client.send_message(chat_id=CHAT_ID, text=message)


def main():
    try:
        bot_client = telegram.Bot(token=TELEGRAM_TOKEN)
        logger.debug("Telegram-bot initializated")
    except Exception as error:
        logger.error(error, exc_info=True)
    current_timestamp = 1612522563  # int(time.time())
    errors_counter = 0
    old_hw_status = None
    while True:
        try:
            new_homework = get_homework_statuses(current_timestamp)
            if new_homework.get("homeworks"):
                errors_counter = 0
                new_hw_status = new_homework.get("homeworks")[0]["status"]
                if new_hw_status != old_hw_status:
                    send_message(
                        parse_homework_status(new_homework.get("homeworks")[0]),
                        bot_client,
                    )
                    old_hw_status = new_hw_status
            current_timestamp = new_homework.get("current_date",
                                                 current_timestamp)
            time.sleep(1200)
        except Exception as error:
            errors_counter += 1
            logger.error(error, exc_info=True)
            time.sleep(5)
            if errors_counter > ERRORS_LIMIT:
                logger.error("Error's limit exceeded")
                send_message(ERRORS_TEXT, bot_client)
                time.sleep(3600)


if __name__ == '__main__':
    main()
