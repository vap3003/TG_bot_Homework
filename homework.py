import logging
import os
import sys
import time
from http import HTTPStatus

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
    """Отправка сообщения в Телеграм чат."""
    try:
        logger.info(f'Попытка отправить сообщение в чат <{TELEGRAM_CHAT_ID}>')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception:
        logger.error('Сбой при отправке сообщения в Telegram')
    logger.info(f'Сообщение <{message}> отправлено в чат <{TELEGRAM_CHAT_ID}>')


def get_api_answer(current_timestamp):
    """Получен ответа от API Практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logger.info('Попытка отправить запрос к API')
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception:
        logger.error('Сбой при отправке запроса к API')
    if homework_statuses.status_code != HTTPStatus.OK:
        raise Exception('Сбой при запросе к эндпоинту')
    return homework_statuses.json()


def check_response(response):
    """Проверка ответа от API практикума."""
    if not (type(response) is dict):
        raise TypeError('Ответ от API имеет некорректный тип')
    if not('homeworks' in response and 'current_date' in response):
        raise ValueError('Отсутствуют подходящие ключи в ответе от API')
    homeworks = response.get('homeworks')
    if not(type(homeworks) is list):
        raise TypeError('Домашки приходят не в виде списка в ответ от API')
    return homeworks


def parse_status(homework):
    """Определение статуса проверки работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    print('homework_name' not in homework)
    if 'status' not in homework:
        raise ValueError('Отсутствует ключ homework_status')
    if 'homework_name' in homework:
        verdict = HOMEWORK_STATUSES[homework_status]
        return (
            f'Изменился статус проверки работы "{homework_name}". {verdict}'
        )
    else:
        verdict = HOMEWORK_STATUSES[homework_status]
        return (
            f'Изменился статус проверки работы. {verdict}'
        )


def check_tokens():
    """Проверк наличия переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_TOKEN))


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствие обязательных переменных окружения!')
        sys.exit('Tokens or Chat ID have not found')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    message_already_sent = False

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                send_message(bot, parse_status(homeworks[0]))
            else:
                logger.info('Отсутствуют данные о домашних работах')
            if message_already_sent:
                message_already_sent = False
            current_timestamp = int(time.time())
        except Exception as error:
            logger.error(f'Ошибка при запросе к основному API: {error}')
            if not message_already_sent:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                message_already_sent = True
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
