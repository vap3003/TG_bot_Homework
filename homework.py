import os
import sys
import time
import logging
import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
)
logger = logging.getLogger()
stream_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


def send_message(bot, message):
    """Отправка сообщения в Телеграм чат"""

    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception:
        logger.error('Сбой при отправке сообщения в Telegram')
    logger.info(f'Сообщение <{message}> отправлено в чат <{TELEGRAM_CHAT_ID}>')


def get_api_answer(current_timestamp):
    """Получен ответа от API Практикума"""

    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if homework_statuses.status_code != 200:
        logger.error('Сбой при запросе к эндпоинту')
        raise Exception('Сбой при запросе к эндпоинту')
    return homework_statuses.json()


def check_response(response):
    """Проверка ответа от API практикума"""

    if type(response['homeworks']) == list:
        return response['homeworks']
    else:
        raise Exception('Домашки приходят не в виде списка в ответ от API')


def parse_status(homework):
    """Определение статуса проверки работы"""

    homework_name = homework['homework_name']
    homework_status = homework['status']
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except ValueError:
        logger.error(f'Недокументированный статус домашней работы: {homework_status}')
    return (
        f'Изменился статус проверки работы '+
        f'"{homework_name}". {verdict}'
    )


def check_tokens():
    """Проверк наличия переменных окружения"""

    if PRACTICUM_TOKEN and TELEGRAM_CHAT_ID and TELEGRAM_TOKEN:
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""

    if check_tokens():
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        message_already_sent = False
    else:
        logger.critical('Отсутствие обязательных переменных окружения!')
        raise Exception('Tokens or Chat ID have not found')

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                send_message(bot, parse_status(homework))
            if message_already_sent:
                message_already_sent = False
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        except Exception as error:
            logger.error(f'Ошибка при запросе к основному API: {error}')
            if not message_already_sent:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                message_already_sent = True
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
