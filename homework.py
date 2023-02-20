import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

from exceptions import Not200Error, ConnectionError


load_dotenv()

secret_token = os.getenv('TOKEN')


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = os.getenv('RETRY_TIME', 600)
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
        logging.info(f'Попытка отправить сообщение {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение {message}')
    except telegram.error.TelegramError as error:
        logging.error(error)


def get_api_answer(timestamp):
    """Получение ответа от API."""
    payload = {'from_date': timestamp}
    try:
        logging.info(f'Попытка получения API ({ENDPOINT, HEADERS})')
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=payload)
    except Exception as error:
        raise ConnectionError(
            f'Ошибка при запросе к основному API: {error}'
        ) from error
    if response.status_code != HTTPStatus.OK:
        raise Not200Error(
            f'Код ответа при запросе к API {response.status_code}'
        )
    response = response.json()
    return response


def check_response(response):
    """Проверка корректности ответа от API."""
    logging.info('Попытка получения ответа от API')
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
        sys.exit('Ошибка токенов')
    try:
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
    except Exception as error:
        raise ConnectionError(
            f'Ошибка при доступе к токену: {error}'
        ) from error
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            homework_status = parse_status(homeworks)

        except (Exception, Not200Error, ConnectionError) as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message, exc_info=True)
        else:
            send_message(bot, homework_status)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    main()
