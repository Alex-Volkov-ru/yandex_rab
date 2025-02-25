import os
import time
import logging
import requests
import telebot

from dotenv import load_dotenv
from telebot import apihelper

load_dotenv()

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


class HomeworkBotError(Exception):
    """Базовый класс исключений для бота."""


class APIResponseError(HomeworkBotError):
    """Ошибка ответа API."""


def check_tokens():
    """Проверяет доступность переменных окружения."""
    missing_tokens = []
    if not PRACTICUM_TOKEN:
        missing_tokens.append('PRACTICUM_TOKEN')
    if not TELEGRAM_TOKEN:
        missing_tokens.append('TELEGRAM_TOKEN')
    if not TELEGRAM_CHAT_ID:
        missing_tokens.append('TELEGRAM_CHAT_ID')

    if missing_tokens:
        logging.critical(
            f'Отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_tokens)}')
        return False
    return True


def send_message(bot, message):
    """Отправляет сообщение в Telegram. Возвращает True, если успешно."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: {message}')
        return True
    except apihelper.ApiException as error:
        logging.error(
            f'Ошибка при отправке сообщения в Telegram: '
            f'{error}, сообщение: {message}'
        )
    except requests.RequestException as error:
        logging.error(
            f'Ошибка при отправке сообщения в Telegram: '
            f'{error}, сообщение: {message}'
        )
    return False  # Если сообщение не отправилось


def get_api_answer(timestamp):
    """Делает запрос к API сервиса Практикум Домашка."""
    params = {'from_date': timestamp}
    response = None
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.RequestException as error:
        raise APIResponseError(
            f'Ошибка при запросе к API: {error}, параметры запроса: {params}, '
            f'ENDPOINT: {ENDPOINT}, HEADERS: {HEADERS}'
        )

    # Перемещаем проверку кода состояния сюда, вне блока try/except
    if response.status_code != 200:
        raise APIResponseError(
            f'Ошибка API: {response.status_code}, {response.text}, '
            f'Параметры запроса: {params}, '
            f'ENDPOINT: {ENDPOINT}, HEADERS: {HEADERS}'
        )

    # Пытаемся распарсить JSON
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(f'Ответ API должен быть словарем, '
                        f'но получен {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks" в ответе API')
    if not isinstance(response['homeworks'], list):
        raise TypeError(f'Значение ключа "homeworks" должно быть списком, '
                        f'но получен {type(response["homeworks"])}')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name"')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status"')

    homework_name = homework['homework_name']
    status = homework['status']

    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы: {status}')

    return (
        f'Изменился статус проверки работы "{homework_name}". '
        f'{HOMEWORK_VERDICTS[status]}'
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        exit()

    bot = telebot.TeleBot(TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = None
    last_message = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)

            # Обновляем timestamp, если есть ключ "current_date" в ответе
            timestamp = response.get('current_date', int(time.time()))

            if homeworks:
                message = parse_status(homeworks[0])

                # Проверяем, не отправляли ли мы уже такое сообщение
                if message != last_message:
                    if send_message(bot, message):
                        last_message = message  # Обновляем last_message
            else:
                logging.debug('Новых статусов нет')

        except HomeworkBotError as error:
            logging.error(f'Сбой в работе программы: {error}')
            if last_error != str(error):
                # Отправляем сообщение и проверяем, было ли оно отправлено
                if send_message(bot, f'Сбой в работе программы: {error}'):
                    last_error = str(error)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[logging.StreamHandler()]
    )
    main()
