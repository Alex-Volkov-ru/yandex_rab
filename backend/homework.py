"""
Модуль Telegram-бота для проверки статуса домашней работы.

На платформе Яндекс.Практикум.
"""
import os
import time
import logging
import requests
import threading
import telebot

from dotenv import load_dotenv
from telebot import apihelper
from telebot import types

# Загружаем переменные окружения
load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Настройки API
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
MAX_RETRIES = 5
RETRY_PERIOD = 600  # 10 минут

# Создаём бота один раз!
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Возможные статусы домашней работы
HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


class HomeworkBotError(Exception):
    """Базовый класс ошибок бота."""


class APIResponseError(HomeworkBotError):
    """Ошибка при запросе к API."""


def check_tokens():
    """Проверяет наличие всех необходимых токенов."""
    missing_tokens = [
        token for token, value in {
            'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
            'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
            'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
        }.items() if not value
    ]
    if missing_tokens:
        logging.critical(f'Отсутствуют токены: {", ".join(missing_tokens)}')
        return False
    return True


def send_message(message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(f'Бот отправил сообщение: {message}')
        return True
    except (apihelper.ApiException, requests.RequestException) as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')
    return False


def get_api_answer(timestamp):
    """Запрашивает статус домашней работы через API."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != 200:
            raise APIResponseError(
                f'Ошибка API: {response.status_code}, {response.text}')
        return response.json()
    except requests.RequestException as error:
        raise APIResponseError(f'Ошибка запроса: {error}')


def check_response(response):
    """Проверяет корректность ответа API."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ API должен быть dict, но получен {type(response)}')
    if 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "homeworks" в ответе API')
    if not isinstance(response['homeworks'], list):
        raise TypeError(
            f'"homeworks" должен быть списком, '
            f'но получен {type(response["homeworks"])}')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус домашней работы из ответа API."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name"')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status"')

    homework_name = homework['homework_name']
    status = homework['status']

    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус: {status}')

    return (
        f'Статус работы "{homework_name}": '
        f'{HOMEWORK_VERDICTS[status]}'
    )


@bot.message_handler(commands=['status'])
def handle_status(message):
    """Обработчик команды /status."""
    send_homework_status()


@bot.message_handler(
    func=lambda message: message.text.lower() == 'проверить статус домашнего задания'
)
def handle_button_status(message):
    """Обработчик кнопки проверки статуса."""
    send_homework_status()


@bot.message_handler(func=lambda message: True)
def send_status_keyboard(message):
    """Отправляет клавиатуру с кнопкой проверки статуса."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton('Проверить статус домашнего задания')
    keyboard.add(button)
    bot.send_message(
        message.chat.id,
        "Нажмите кнопку, чтобы проверить статус домашнего задания.",
        reply_markup=keyboard
    )


def send_homework_status():
    """Отправляет статус домашней работы пользователю."""
    try:
        # Запрашиваем данные за последний час (3600 секунд)
        timestamp = int(time.time()) - 3600
        response = get_api_answer(timestamp)
        homeworks = check_response(response)

        if homeworks:
            # Сортируем работы по дате обновления (новые сначала)
            homeworks_sorted = sorted(
                homeworks,
                key=lambda x: x.get('date_updated', 0),
                reverse=True
            )
            latest_homework = homeworks_sorted[0]

            # Формируем расширенное сообщение
            status = latest_homework['status']
            homework_name = latest_homework['homework_name']
            message = (
                f"Работа: {homework_name}\n"
                f"Статус: {HOMEWORK_VERDICTS[status]}\n"
                f"Последнее обновление: {time.ctime(latest_homework.get('date_updated', time.time()))}"
            )
        else:
            message = "Данные о домашней работе ещё не получены. Попробуйте позже."

    except HomeworkBotError as error:
        message = f"Ошибка при получении статуса: {error}"
    except Exception as error:
        message = f"Неожиданная ошибка: {error}"

    send_message(message)


def main():
    """Основной цикл работы бота."""
    if not check_tokens():
        exit()

    timestamp = int(time.time())
    last_status = None

    def start_polling():
        """Запускает long polling для Telegram-бота."""
        while True:
            try:
                bot.polling(none_stop=True, interval=5, timeout=30)
            except Exception as error:
                logging.error(f'Ошибка бота: {error}')
                time.sleep(10)

    thread = threading.Thread(target=start_polling, daemon=True)
    thread.start()

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            current_timestamp = response.get('current_date', int(time.time()))

            if homeworks:
                # Сортируем по дате обновления
                homeworks_sorted = sorted(
                    homeworks,
                    key=lambda x: x.get('date_updated', 0),
                    reverse=True
                )
                current_status = homeworks_sorted[0]['status']

                if current_status != last_status:
                    message = (
                        f"Статус изменён!\n"
                        f"Работа: {homeworks_sorted[0]['homework_name']}\n"
                        f"Новый статус: {HOMEWORK_VERDICTS[current_status]}"
                    )
                    if send_message(message):
                        last_status = current_status
                        timestamp = current_timestamp
            else:
                logging.info('Новых статусов нет')

        except Exception as error:
            logging.error(f'Ошибка: {error}')
            time.sleep(RETRY_PERIOD)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    main()
