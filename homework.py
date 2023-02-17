import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv


load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)
secret_token = os.getenv('TOKEN')


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """проверяет доступность переменных окружения необходимых для работы."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    return all(tokens)


def send_message(bot, message):
    """отправляет сообщение в Telegram чат."""
    try:
        logging.debug(f'Бот отправил сообщение {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(error)


def get_api_answer(timestamp):
    """Получение ответа от API."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
    if response.status_code != HTTPStatus.OK:
        raise TypeError(
            f'Код ответа при запросе к API {response.status_code}'
        )
    response = response.json()
    return response


def check_response(response):
    """Проверка корректности ответа от API."""
    if not isinstance(response, dict):
        raise TypeError('not dict после .json() в ответе API')
    if not isinstance(response.get('homeworks'), list):
        logging.error('отсутствие ключа homeworks')
        raise TypeError('not list в ответе API по ключу homeworks')
    if not response.get('homeworks'):
        logging.debug('отсутствие новых статусов')
        raise TypeError('Новых статусов нет')
    return response['homeworks'][0]


def parse_status(homework):
    """Получение статуса домашней работы."""
    if not isinstance(homework, dict):
        raise TypeError('не словарь после .json() в ответе API')
    homework_name = homework.get('homework_name')
    if len(homework_name) == 0:
        raise TypeError('в ответе API домашки нет ключа homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        logging.error('отсутствие статуса в словаре')
        raise TypeError('статус отсутствует в словаре')
    verdict = HOMEWORK_VERDICTS[homework_status]

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутствие обязательных переменных окружения')
        raise TypeError('Ошибка токенов')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            homework_status = parse_status(homeworks)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
        else:
            send_message(bot, homework_status)
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
